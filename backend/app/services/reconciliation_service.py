import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.models.reconciliation_match import ReconciliationMatch
from app.models.job import Job

logger = logging.getLogger(__name__)

SUGGESTION_THRESHOLD = 40.0  # Show as suggestion
AUTO_CONFIRM_THRESHOLD = 80.0  # Auto-confirm


async def run_reconciliation(client_id: uuid.UUID, job_id: uuid.UUID):
    """Background task: find unmatched invoices + transactions, score pairs, create matches."""
    async with async_session() as db:
        try:
            # Load job and mark as processing
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            job.status = "processing"
            await db.commit()

            # Load client for GSTIN
            result = await db.execute(select(Client).where(Client.id == client_id))
            client = result.scalar_one_or_none()
            if not client:
                logger.error(f"Client {client_id} not found")
                job.status = "failed"
                job.error_message = "Client not found"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Load unmatched invoices (completed processing, active, unmatched)
            result = await db.execute(
                select(Invoice).where(
                    Invoice.client_id == client_id,
                    Invoice.is_active == True,
                    Invoice.processing_status == "completed",
                    Invoice.recon_status == "unmatched",
                )
            )
            invoices = list(result.scalars().all())

            # Load unmatched transactions
            result = await db.execute(
                select(Transaction).where(
                    Transaction.client_id == client_id,
                    Transaction.recon_status == "unmatched",
                )
            )
            transactions = list(result.scalars().all())

            if not invoices or not transactions:
                job.status = "completed"
                job.result_summary = (
                    f"No matches possible: {len(invoices)} unmatched invoices, "
                    f"{len(transactions)} unmatched transactions"
                )
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Score all pairs and create matches above threshold
            matches_created = 0
            auto_confirmed = 0

            for invoice in invoices:
                for txn in transactions:
                    # Skip if invoice type doesn't align with transaction type
                    # Sales invoices match credit transactions; purchase invoices match debit
                    if invoice.invoice_type == "sales" and txn.transaction_type != "credit":
                        continue
                    if invoice.invoice_type == "purchase" and txn.transaction_type != "debit":
                        continue

                    score = _compute_confidence(invoice, txn, client)

                    if score < SUGGESTION_THRESHOLD:
                        continue

                    # Check if this pair already has a match
                    existing = await db.execute(
                        select(ReconciliationMatch).where(
                            ReconciliationMatch.invoice_id == invoice.id,
                            ReconciliationMatch.transaction_id == txn.id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    is_confirmed = score >= AUTO_CONFIRM_THRESHOLD
                    matched_amount = invoice.total_amount if invoice.total_amount else Decimal("0")

                    match = ReconciliationMatch(
                        id=uuid.uuid4(),
                        client_id=client_id,
                        invoice_id=invoice.id,
                        transaction_id=txn.id,
                        confidence_score=Decimal(str(round(score, 2))),
                        matched_amount=matched_amount,
                        is_confirmed=is_confirmed,
                        match_method="auto",
                    )
                    db.add(match)
                    matches_created += 1
                    if is_confirmed:
                        auto_confirmed += 1

            # Flush to persist matches before updating statuses
            await db.flush()

            # Update recon_status on invoices that got matched
            for invoice in invoices:
                match_count = await db.execute(
                    select(func.count()).select_from(ReconciliationMatch).where(
                        ReconciliationMatch.invoice_id == invoice.id,
                        ReconciliationMatch.is_confirmed == True,
                    )
                )
                if match_count.scalar() > 0:
                    invoice.recon_status = "matched"

            # Update recon_status on transactions that got matched
            for txn in transactions:
                match_count = await db.execute(
                    select(func.count()).select_from(ReconciliationMatch).where(
                        ReconciliationMatch.transaction_id == txn.id,
                        ReconciliationMatch.is_confirmed == True,
                    )
                )
                if match_count.scalar() > 0:
                    txn.recon_status = "matched"

            # Complete job
            job.status = "completed"
            job.result_summary = (
                f"Created {matches_created} matches ({auto_confirmed} auto-confirmed) "
                f"from {len(invoices)} invoices and {len(transactions)} transactions"
            )
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                f"Reconciliation for client {client_id}: "
                f"{matches_created} matches, {auto_confirmed} auto-confirmed"
            )

            # Fire notification (fire-and-forget)
            try:
                from app.services.notification_service import notify
                await notify(
                    client_id=client_id,
                    accountant_id=client.accountant_id,
                    trigger_event="reconciliation_complete",
                    context_data={
                        "matched_count": str(matches_created),
                    },
                )
            except Exception:
                logger.debug("Notification dispatch failed (non-critical)", exc_info=True)

        except Exception as e:
            logger.exception(f"Error running reconciliation for client {client_id}: {e}")
            await db.rollback()
            # Try to mark job as failed in separate session
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


def _compute_confidence(invoice: Invoice, transaction: Transaction, client: Client) -> float:
    """Score a potential match 0-100."""
    score = 0.0

    inv_amount = float(invoice.total_amount) if invoice.total_amount else None
    txn_amount = float(transaction.amount)

    # --- Amount match (45 points) ---
    if inv_amount is not None and txn_amount > 0:
        diff = abs(inv_amount - txn_amount)
        if diff <= 1.0:
            score += 45
        elif inv_amount > 0:
            pct_diff = diff / inv_amount
            if pct_diff <= 0.02:
                score += 30
            elif pct_diff <= 0.05:
                score += 15

    # --- Date proximity (25 points) ---
    inv_date = invoice.invoice_date
    txn_date = transaction.transaction_date
    if inv_date and txn_date:
        day_diff = abs((txn_date - inv_date).days)
        if day_diff == 0:
            score += 25
        elif day_diff <= 3:
            score += 20
        elif day_diff <= 7:
            score += 15
        elif day_diff <= 14:
            score += 10

    # --- GSTIN / counterparty match (15 points) ---
    txn_desc = (transaction.raw_description or "").upper()
    txn_counterparty = (transaction.parsed_counterparty or "").upper()

    # For sales: match buyer info against transaction; for purchase: match seller
    if invoice.invoice_type == "sales":
        match_gstin = (invoice.buyer_gstin or "").upper()
        match_name = (invoice.buyer_name or "").upper()
    else:
        match_gstin = (invoice.seller_gstin or "").upper()
        match_name = (invoice.seller_name or "").upper()

    if match_gstin and match_gstin in txn_desc:
        score += 15
    elif match_name and len(match_name) >= 3:
        # Check if name appears in counterparty or description
        if match_name in txn_counterparty or match_name in txn_desc:
            score += 15
        else:
            # Try partial match (first word of name)
            first_word = match_name.split()[0] if match_name.split() else ""
            if first_word and len(first_word) >= 4 and first_word in txn_counterparty:
                score += 8

    # --- Reference match (15 points) ---
    inv_number = (invoice.invoice_number or "").upper().strip()
    if inv_number and len(inv_number) >= 3:
        if inv_number in txn_desc:
            score += 15
        elif len(inv_number) >= 5:
            # Try without common prefixes like INV-, GST-
            stripped = inv_number
            for prefix in ("INV-", "INV/", "GST-", "GST/", "#"):
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):]
                    break
            if stripped and stripped in txn_desc:
                score += 8

    return score
