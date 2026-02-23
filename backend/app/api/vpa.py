import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.job import Job
from app.models.transaction import Transaction
from app.models.vpa_entry import VpaEntry
from app.schemas.job import JobResponse
from app.schemas.vpa import (
    CashfreeVerifyResponse,
    VpaEntryCreate,
    VpaEntryResponse,
    VpaEntryUpdate,
    VpaResolutionSummary,
)
from app.services.vpa_service import run_vpa_resolution, resolve_single_vpa

router = APIRouter(prefix="/clients/{client_id}/vpa", tags=["vpa"])


async def _verify_client_ownership(
    client_id: uuid.UUID, current_user: Accountant, db: AsyncSession
) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.accountant_id == current_user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("", response_model=list[VpaEntryResponse])
async def list_vpa_entries(
    client_id: uuid.UUID,
    is_verified: bool | None = Query(None),
    source: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List VPA entries for a client with optional filters."""
    await _verify_client_ownership(client_id, current_user, db)

    query = select(VpaEntry).where(
        VpaEntry.client_id == client_id,
        VpaEntry.is_active == True,
    )

    if is_verified is not None:
        query = query.where(VpaEntry.is_verified == is_verified)
    if source:
        query = query.where(VpaEntry.source == source)
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(
            (VpaEntry.vpa.ilike(search_term))
            | (VpaEntry.resolved_name.ilike(search_term))
            | (VpaEntry.gstin.ilike(search_term))
        )

    query = query.order_by(VpaEntry.transaction_count.desc(), VpaEntry.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/summary", response_model=VpaResolutionSummary)
async def get_vpa_summary(
    client_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get VPA resolution summary stats."""
    await _verify_client_ownership(client_id, current_user, db)

    # VPA entry stats
    total_result = await db.execute(
        select(func.count()).select_from(VpaEntry).where(
            VpaEntry.client_id == client_id, VpaEntry.is_active == True
        )
    )
    total_vpa = total_result.scalar() or 0

    verified_result = await db.execute(
        select(func.count()).select_from(VpaEntry).where(
            VpaEntry.client_id == client_id, VpaEntry.is_active == True, VpaEntry.is_verified == True
        )
    )
    verified = verified_result.scalar() or 0

    # UPI transaction stats
    total_upi_result = await db.execute(
        select(func.count()).select_from(Transaction).where(
            Transaction.client_id == client_id,
            Transaction.parsed_upi_id.isnot(None),
            Transaction.parsed_upi_id != "",
        )
    )
    total_upi = total_upi_result.scalar() or 0

    tagged_result = await db.execute(
        select(func.count()).select_from(Transaction).where(
            Transaction.client_id == client_id,
            Transaction.parsed_upi_id.isnot(None),
            Transaction.parsed_upi_id != "",
            Transaction.vpa_entry_id.isnot(None),
        )
    )
    tagged = tagged_result.scalar() or 0

    # Sources breakdown
    sources_result = await db.execute(
        select(VpaEntry.source, func.count())
        .where(VpaEntry.client_id == client_id, VpaEntry.is_active == True)
        .group_by(VpaEntry.source)
    )
    sources_breakdown = {row[0]: row[1] for row in sources_result.all()}

    return VpaResolutionSummary(
        total_vpa_entries=total_vpa,
        verified_count=verified,
        unverified_count=total_vpa - verified,
        total_upi_transactions=total_upi,
        tagged_transactions=tagged,
        untagged_transactions=total_upi - tagged,
        sources_breakdown=sources_breakdown,
    )


@router.post("", response_model=VpaEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_vpa_entry(
    client_id: uuid.UUID,
    data: VpaEntryCreate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a VPA entry (source=manual, is_verified=True)."""
    await _verify_client_ownership(client_id, current_user, db)

    entry = await resolve_single_vpa(
        db,
        client_id=client_id,
        vpa=data.vpa,
        source="manual",
        name=data.resolved_name,
        gstin=data.gstin,
    )
    if data.notes:
        entry.notes = data.notes
    await db.flush()
    await db.refresh(entry)
    return entry


@router.put("/{vpa_id}", response_model=VpaEntryResponse)
async def update_vpa_entry(
    client_id: uuid.UUID,
    vpa_id: uuid.UUID,
    data: VpaEntryUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a VPA entry."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.id == vpa_id,
            VpaEntry.client_id == client_id,
            VpaEntry.is_active == True,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="VPA entry not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    # Auto-extract PAN from GSTIN
    if data.gstin and len(data.gstin) >= 12:
        entry.pan = data.gstin[2:12]

    entry.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{vpa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vpa_entry(
    client_id: uuid.UUID,
    vpa_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a VPA entry and unlink transactions."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.id == vpa_id,
            VpaEntry.client_id == client_id,
            VpaEntry.is_active == True,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="VPA entry not found")

    entry.is_active = False
    entry.updated_at = datetime.now(timezone.utc)

    # Unlink transactions
    await db.execute(
        update(Transaction)
        .where(Transaction.vpa_entry_id == vpa_id)
        .values(vpa_entry_id=None)
    )


@router.post("/resolve", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_vpa_resolution(
    client_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger full VPA resolution as a background job."""
    await _verify_client_ownership(client_id, current_user, db)

    job = Job(
        id=uuid.uuid4(),
        client_id=client_id,
        job_type="vpa_resolution",
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    background_tasks.add_task(run_vpa_resolution, client_id, job.id)
    return job


@router.post("/{vpa_id}/verify", response_model=CashfreeVerifyResponse)
async def verify_vpa_cashfree(
    client_id: uuid.UUID,
    vpa_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a single VPA via Cashfree API."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.id == vpa_id,
            VpaEntry.client_id == client_id,
            VpaEntry.is_active == True,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="VPA entry not found")

    from app.services.cashfree_service import verify_vpa

    verification = await verify_vpa(entry.vpa)

    # Update entry with Cashfree result
    if verification["is_valid"]:
        if verification["registered_name"]:
            entry.resolved_name = verification["registered_name"]
        entry.confidence = Decimal("95")
        entry.source = "cashfree"
        entry.is_verified = True
    entry.updated_at = datetime.now(timezone.utc)

    return CashfreeVerifyResponse(
        vpa=verification["vpa"],
        registered_name=verification["registered_name"],
        is_valid=verification["is_valid"],
        source=verification["source"],
    )


@router.post("/collect", status_code=status.HTTP_200_OK)
async def send_vpa_collection_request(
    client_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a VPA collection request notification to the client."""
    client = await _verify_client_ownership(client_id, current_user, db)

    # Count unresolved VPAs (no resolved_name)
    unresolved_result = await db.execute(
        select(VpaEntry).where(
            VpaEntry.client_id == client_id,
            VpaEntry.is_active == True,
            VpaEntry.resolved_name.is_(None),
        )
    )
    unresolved = list(unresolved_result.scalars().all())

    if not unresolved:
        return {"status": "ok", "message": "No unresolved VPAs to collect"}

    # Build vendor list from VPAs
    vendor_list = ", ".join(entry.vpa for entry in unresolved[:10])
    if len(unresolved) > 10:
        vendor_list += f" (+{len(unresolved) - 10} more)"

    try:
        from app.services.notification_service import notify
        await notify(
            client_id=client_id,
            accountant_id=current_user.id,
            trigger_event="vpa_collection_request",
            context_data={
                "unresolved_count": str(len(unresolved)),
                "vendor_list": vendor_list,
            },
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to send collection request. Check messaging configuration.",
        )

    return {
        "status": "ok",
        "message": f"Collection request sent for {len(unresolved)} unresolved VPAs",
    }
