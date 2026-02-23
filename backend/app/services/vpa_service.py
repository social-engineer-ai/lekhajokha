"""VPA resolution service — triangulates UPI VPA identity from multiple sources."""

import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.invoice import Invoice
from app.models.job import Job
from app.models.message import Message
from app.models.reconciliation_match import ReconciliationMatch
from app.models.transaction import Transaction
from app.models.vpa_entry import VpaEntry

logger = logging.getLogger(__name__)

# Source priority: higher-trust sources overwrite lower
SOURCE_PRIORITY = {
    "reconciliation": 5,
    "cashfree": 4,
    "transaction_aggregate": 3,
    "whatsapp_profile": 2,
    "manual": 1,
}


async def run_vpa_resolution(client_id: uuid.UUID, job_id: uuid.UUID):
    """Background task: full VPA resolution from all sources.
    Uses its own DB session (not the request's session).
    """
    async with async_session() as db:
        try:
            # Load job and mark processing
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            job.status = "processing"
            await db.commit()

            # Step 1: Resolve from transaction descriptions
            txn_count = await _resolve_from_transactions(db, client_id)
            logger.info(f"VPA resolution step 1 (transactions): {txn_count} entries")

            # Step 2: Resolve from reconciliation matches
            recon_count = await _resolve_from_reconciliation(db, client_id)
            logger.info(f"VPA resolution step 2 (reconciliation): {recon_count} entries")

            # Step 3: Resolve from WhatsApp profile names
            wa_count = await _resolve_from_whatsapp(db, client_id)
            logger.info(f"VPA resolution step 3 (whatsapp): {wa_count} entries")

            # Step 4: Tag transactions with resolved VPAs
            tagged = await _tag_transactions(db, client_id)
            logger.info(f"VPA resolution step 4 (tagging): {tagged} transactions tagged")

            total = txn_count + recon_count + wa_count

            job.status = "completed"
            job.result_summary = (
                f"Resolved {total} VPA entries "
                f"(txn: {txn_count}, recon: {recon_count}, whatsapp: {wa_count}). "
                f"Tagged {tagged} transactions."
            )
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            logger.exception(f"Error running VPA resolution for client {client_id}: {e}")
            await db.rollback()
            try:
                async with async_session() as err_db:
                    result = await err_db.execute(select(Job).where(Job.id == job_id))
                    j = result.scalar_one_or_none()
                    if j:
                        j.status = "failed"
                        j.error_message = str(e)[:500]
                        j.completed_at = datetime.now(timezone.utc)
                    await err_db.commit()
            except Exception:
                logger.exception("Failed to update error status")


async def _resolve_from_transactions(db: AsyncSession, client_id: uuid.UUID) -> int:
    """Aggregate parsed_upi_id from transactions.
    Confidence: 50 + min(count*5, 30), source=transaction_aggregate.
    """
    # Group transactions by parsed_upi_id
    result = await db.execute(
        select(
            Transaction.parsed_upi_id,
            func.count().label("cnt"),
            func.max(Transaction.parsed_counterparty).label("counterparty"),
            func.max(Transaction.transaction_date).label("last_seen"),
        )
        .where(
            Transaction.client_id == client_id,
            Transaction.parsed_upi_id.isnot(None),
            Transaction.parsed_upi_id != "",
        )
        .group_by(Transaction.parsed_upi_id)
    )
    rows = result.all()

    count = 0
    for row in rows:
        vpa = row.parsed_upi_id.strip().lower()
        if "@" not in vpa:
            continue

        txn_count = row.cnt
        confidence = Decimal(str(50 + min(txn_count * 5, 30)))

        count += await _upsert_vpa_entry(
            db,
            client_id=client_id,
            vpa=vpa,
            source="transaction_aggregate",
            confidence=confidence,
            resolved_name=row.counterparty,
            transaction_count=txn_count,
            last_seen_at=row.last_seen,
        )

    await db.flush()
    return count


async def _resolve_from_reconciliation(db: AsyncSession, client_id: uuid.UUID) -> int:
    """Join ReconciliationMatch + Transaction + Invoice to extract GSTIN.
    Confidence: 85, source=reconciliation.
    """
    result = await db.execute(
        select(
            Transaction.parsed_upi_id,
            Invoice.seller_gstin,
            Invoice.buyer_gstin,
            Invoice.seller_name,
            Invoice.buyer_name,
            Invoice.invoice_type,
        )
        .join(ReconciliationMatch, ReconciliationMatch.transaction_id == Transaction.id)
        .join(Invoice, ReconciliationMatch.invoice_id == Invoice.id)
        .where(
            ReconciliationMatch.client_id == client_id,
            ReconciliationMatch.is_confirmed == True,
            Transaction.parsed_upi_id.isnot(None),
            Transaction.parsed_upi_id != "",
        )
    )
    rows = result.all()

    count = 0
    for row in rows:
        vpa = row.parsed_upi_id.strip().lower()
        if "@" not in vpa:
            continue

        # For sales invoices, counterparty is buyer; for purchase, counterparty is seller
        if row.invoice_type == "sales":
            gstin = row.buyer_gstin
            name = row.buyer_name
        else:
            gstin = row.seller_gstin
            name = row.seller_name

        pan = gstin[2:12] if gstin and len(gstin) >= 12 else None

        count += await _upsert_vpa_entry(
            db,
            client_id=client_id,
            vpa=vpa,
            source="reconciliation",
            confidence=Decimal("85"),
            resolved_name=name,
            gstin=gstin,
            pan=pan,
        )

    await db.flush()
    return count


async def _resolve_from_whatsapp(db: AsyncSession, client_id: uuid.UUID) -> int:
    """Query inbound WhatsApp messages with profile names.
    Conservative matching: check if profile name contains any known VPA local part.
    Confidence cap: 50.
    """
    # Get inbound WhatsApp messages with profile names
    result = await db.execute(
        select(Message.whatsapp_profile_name, Message.content)
        .where(
            Message.client_id == client_id,
            Message.channel == "whatsapp",
            Message.direction == "inbound",
            Message.whatsapp_profile_name.isnot(None),
            Message.whatsapp_profile_name != "",
        )
    )
    messages = result.all()

    if not messages:
        return 0

    # Get existing unresolved VPA entries for this client
    vpa_result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.client_id == client_id,
            VpaEntry.is_active == True,
            VpaEntry.resolved_name.is_(None),
        )
    )
    unresolved_vpas = list(vpa_result.scalars().all())

    if not unresolved_vpas:
        return 0

    count = 0
    for msg in messages:
        profile_name = msg.whatsapp_profile_name.strip()
        if not profile_name:
            continue

        profile_upper = profile_name.upper()

        for vpa_entry in unresolved_vpas:
            # Check if profile name contains VPA local part (before @)
            local_part = vpa_entry.vpa.split("@")[0].upper()
            if len(local_part) >= 3 and local_part in profile_upper:
                # Only update if current source is lower priority
                if SOURCE_PRIORITY.get(vpa_entry.source, 0) < SOURCE_PRIORITY.get("whatsapp_profile", 0):
                    vpa_entry.resolved_name = profile_name
                    vpa_entry.source = "whatsapp_profile"
                    vpa_entry.confidence = min(Decimal("50"), vpa_entry.confidence)
                    count += 1
                elif vpa_entry.source == "whatsapp_profile" and not vpa_entry.resolved_name:
                    vpa_entry.resolved_name = profile_name
                    count += 1

    await db.flush()
    return count


async def _tag_transactions(db: AsyncSession, client_id: uuid.UUID) -> int:
    """Match parsed_upi_id on transactions to VpaEntry, set vpa_entry_id.
    Batch updates in chunks of 500.
    """
    # Load VPA directory for this client
    result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.client_id == client_id,
            VpaEntry.is_active == True,
        )
    )
    vpa_entries = {e.vpa: e for e in result.scalars().all()}

    if not vpa_entries:
        return 0

    # Load untagged UPI transactions
    result = await db.execute(
        select(Transaction.id, Transaction.parsed_upi_id)
        .where(
            Transaction.client_id == client_id,
            Transaction.parsed_upi_id.isnot(None),
            Transaction.parsed_upi_id != "",
            Transaction.vpa_entry_id.is_(None),
        )
    )
    untagged = result.all()

    tagged = 0
    batch = []

    for txn_id, parsed_upi_id in untagged:
        vpa = parsed_upi_id.strip().lower()
        entry = vpa_entries.get(vpa)
        if entry:
            batch.append({"txn_id": txn_id, "vpa_entry_id": entry.id})
            tagged += 1

        if len(batch) >= 500:
            await _batch_update_vpa_entry_ids(db, batch)
            batch = []

    if batch:
        await _batch_update_vpa_entry_ids(db, batch)

    # Update transaction counts on VPA entries
    for entry in vpa_entries.values():
        count_result = await db.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.vpa_entry_id == entry.id)
        )
        entry.transaction_count = count_result.scalar() or 0

    await db.flush()
    return tagged


async def _batch_update_vpa_entry_ids(db: AsyncSession, batch: list[dict]):
    """Update vpa_entry_id for a batch of transactions."""
    for item in batch:
        await db.execute(
            update(Transaction)
            .where(Transaction.id == item["txn_id"])
            .values(vpa_entry_id=item["vpa_entry_id"])
        )
    await db.flush()


async def _upsert_vpa_entry(
    db: AsyncSession,
    client_id: uuid.UUID,
    vpa: str,
    source: str,
    confidence: Decimal,
    resolved_name: str | None = None,
    gstin: str | None = None,
    pan: str | None = None,
    transaction_count: int | None = None,
    last_seen_at=None,
) -> int:
    """Create or update a VPA entry. Returns 1 if created/updated, 0 if skipped."""
    result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.client_id == client_id,
            VpaEntry.vpa == vpa,
            VpaEntry.is_active == True,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Only update if new source has higher or equal priority
        existing_priority = SOURCE_PRIORITY.get(existing.source, 0)
        new_priority = SOURCE_PRIORITY.get(source, 0)

        if new_priority >= existing_priority:
            if resolved_name and not existing.resolved_name:
                existing.resolved_name = resolved_name
            if gstin and not existing.gstin:
                existing.gstin = gstin
                if not existing.pan and gstin and len(gstin) >= 12:
                    existing.pan = gstin[2:12]
            if pan and not existing.pan:
                existing.pan = pan
            if float(confidence) > float(existing.confidence):
                existing.confidence = confidence
                existing.source = source
            if transaction_count is not None:
                existing.transaction_count = transaction_count
            if last_seen_at is not None:
                existing.last_seen_at = last_seen_at
            return 1
        return 0

    # Create new entry
    entry = VpaEntry(
        id=uuid.uuid4(),
        client_id=client_id,
        vpa=vpa,
        resolved_name=resolved_name,
        gstin=gstin,
        pan=pan or (gstin[2:12] if gstin and len(gstin) >= 12 else None),
        source=source,
        confidence=confidence,
        transaction_count=transaction_count or 0,
        last_seen_at=last_seen_at,
    )
    db.add(entry)
    return 1


async def tag_transactions_quick(db: AsyncSession, client_id: uuid.UUID, new_transactions: list):
    """Lightweight: only check new transactions against existing VPA directory.
    Called after statement processing (fire-and-forget).
    """
    try:
        # Load VPA directory
        result = await db.execute(
            select(VpaEntry).where(
                VpaEntry.client_id == client_id,
                VpaEntry.is_active == True,
            )
        )
        vpa_entries = {e.vpa: e for e in result.scalars().all()}

        if not vpa_entries:
            return

        tagged = 0
        for txn in new_transactions:
            if txn.parsed_upi_id and "@" in txn.parsed_upi_id:
                vpa = txn.parsed_upi_id.strip().lower()
                entry = vpa_entries.get(vpa)
                if entry:
                    txn.vpa_entry_id = entry.id
                    entry.transaction_count = (entry.transaction_count or 0) + 1
                    entry.last_seen_at = txn.transaction_date
                    tagged += 1

        if tagged:
            await db.flush()
            logger.info(f"Quick-tagged {tagged} transactions for client {client_id}")

    except Exception as e:
        logger.debug(f"Quick VPA tagging failed (non-critical): {e}", exc_info=True)


async def resolve_single_vpa(
    db: AsyncSession,
    client_id: uuid.UUID,
    vpa: str,
    source: str,
    name: str | None = None,
    gstin: str | None = None,
) -> VpaEntry:
    """Create or update a single VpaEntry."""
    vpa = vpa.strip().lower()
    pan = gstin[2:12] if gstin and len(gstin) >= 12 else None

    confidence_map = {
        "manual": Decimal("100"),
        "cashfree": Decimal("95"),
        "reconciliation": Decimal("85"),
        "transaction_aggregate": Decimal("60"),
        "whatsapp_profile": Decimal("50"),
    }
    confidence = confidence_map.get(source, Decimal("50"))

    result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.client_id == client_id,
            VpaEntry.vpa == vpa,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        if name:
            existing.resolved_name = name
        if gstin:
            existing.gstin = gstin
        if pan:
            existing.pan = pan
        existing.source = source
        existing.confidence = confidence
        if source == "manual":
            existing.is_verified = True
        existing.is_active = True
        await db.flush()
        return existing

    entry = VpaEntry(
        id=uuid.uuid4(),
        client_id=client_id,
        vpa=vpa,
        resolved_name=name,
        gstin=gstin,
        pan=pan,
        source=source,
        confidence=confidence,
        is_verified=(source == "manual"),
    )
    db.add(entry)
    await db.flush()
    return entry
