import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.models.reconciliation_match import ReconciliationMatch
from app.models.job import Job
from app.schemas.reconciliation import (
    InvoiceSummary,
    TransactionSummary,
    ReconciliationMatchResponse,
    ReconciliationMatchCreate,
    ReconciliationMatchUpdate,
    ReconciliationSummary,
)
from app.schemas.job import JobResponse
from app.services.reconciliation_service import run_reconciliation

router = APIRouter(prefix="/clients/{client_id}/reconciliation", tags=["reconciliation"])


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


def _build_match_response(match: ReconciliationMatch, invoice: Invoice, transaction: Transaction) -> ReconciliationMatchResponse:
    return ReconciliationMatchResponse(
        id=match.id,
        client_id=match.client_id,
        invoice_id=match.invoice_id,
        transaction_id=match.transaction_id,
        confidence_score=match.confidence_score,
        matched_amount=match.matched_amount,
        is_confirmed=match.is_confirmed,
        match_method=match.match_method,
        notes=match.notes,
        created_at=match.created_at,
        updated_at=match.updated_at,
        invoice_summary=InvoiceSummary(
            id=invoice.id,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoice_date,
            invoice_type=invoice.invoice_type,
            seller_name=invoice.seller_name,
            buyer_name=invoice.buyer_name,
            total_amount=invoice.total_amount,
        ),
        transaction_summary=TransactionSummary(
            id=transaction.id,
            transaction_date=transaction.transaction_date,
            raw_description=transaction.raw_description,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
            parsed_counterparty=transaction.parsed_counterparty,
            transaction_mode=transaction.transaction_mode,
        ),
    )


@router.post("/run", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_reconciliation(
    client_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger auto-matching reconciliation as a background job."""
    await _verify_client_ownership(client_id, current_user, db)

    job = Job(
        id=uuid.uuid4(),
        client_id=client_id,
        job_type="reconciliation",
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    background_tasks.add_task(run_reconciliation, client_id, job.id)
    return job


@router.get("/summary", response_model=ReconciliationSummary)
async def get_reconciliation_summary(
    client_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get reconciliation dashboard stats."""
    await _verify_client_ownership(client_id, current_user, db)

    # Invoice stats
    inv_base = select(Invoice).where(
        Invoice.client_id == client_id,
        Invoice.is_active == True,
        Invoice.processing_status == "completed",
    )

    total_inv_result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total_amount), 0)).select_from(inv_base.subquery())
    )
    total_inv_row = total_inv_result.one()
    total_invoices = total_inv_row[0]
    total_invoice_amount = Decimal(str(total_inv_row[1]))

    matched_inv_result = await db.execute(
        select(func.count(), func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.client_id == client_id,
            Invoice.is_active == True,
            Invoice.processing_status == "completed",
            Invoice.recon_status == "matched",
        )
    )
    matched_inv_row = matched_inv_result.one()
    matched_invoices = matched_inv_row[0]
    matched_invoice_amount = Decimal(str(matched_inv_row[1]))

    # Transaction stats
    total_txn_result = await db.execute(
        select(func.count()).where(Transaction.client_id == client_id)
    )
    total_transactions = total_txn_result.scalar()

    matched_txn_result = await db.execute(
        select(func.count()).where(
            Transaction.client_id == client_id,
            Transaction.recon_status == "matched",
        )
    )
    matched_transactions = matched_txn_result.scalar()

    return ReconciliationSummary(
        total_invoices=total_invoices,
        matched_invoices=matched_invoices,
        unmatched_invoices=total_invoices - matched_invoices,
        total_transactions=total_transactions,
        matched_transactions=matched_transactions,
        unmatched_transactions=total_transactions - matched_transactions,
        total_invoice_amount=total_invoice_amount,
        matched_invoice_amount=matched_invoice_amount,
        unmatched_invoice_amount=total_invoice_amount - matched_invoice_amount,
    )


@router.get("/matches", response_model=list[ReconciliationMatchResponse])
async def list_matches(
    client_id: uuid.UUID,
    is_confirmed: bool | None = Query(None),
    match_method: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reconciliation matches with filters."""
    await _verify_client_ownership(client_id, current_user, db)

    query = select(ReconciliationMatch).where(ReconciliationMatch.client_id == client_id)

    if is_confirmed is not None:
        query = query.where(ReconciliationMatch.is_confirmed == is_confirmed)
    if match_method:
        query = query.where(ReconciliationMatch.match_method == match_method)

    query = query.order_by(ReconciliationMatch.confidence_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    matches = result.scalars().all()

    # Build responses with summaries
    responses = []
    for match in matches:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == match.invoice_id))
        invoice = inv_result.scalar_one_or_none()
        txn_result = await db.execute(select(Transaction).where(Transaction.id == match.transaction_id))
        transaction = txn_result.scalar_one_or_none()

        if invoice and transaction:
            responses.append(_build_match_response(match, invoice, transaction))

    return responses


@router.post("/matches", response_model=ReconciliationMatchResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_match(
    client_id: uuid.UUID,
    data: ReconciliationMatchCreate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual match between an invoice and a transaction."""
    await _verify_client_ownership(client_id, current_user, db)

    # Verify invoice belongs to client
    inv_result = await db.execute(
        select(Invoice).where(
            Invoice.id == data.invoice_id,
            Invoice.client_id == client_id,
            Invoice.is_active == True,
        )
    )
    invoice = inv_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Verify transaction belongs to client
    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.id == data.transaction_id,
            Transaction.client_id == client_id,
        )
    )
    transaction = txn_result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Check for existing match
    existing = await db.execute(
        select(ReconciliationMatch).where(
            ReconciliationMatch.invoice_id == data.invoice_id,
            ReconciliationMatch.transaction_id == data.transaction_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Match already exists for this invoice-transaction pair")

    matched_amount = data.matched_amount if data.matched_amount is not None else (invoice.total_amount or Decimal("0"))

    match = ReconciliationMatch(
        id=uuid.uuid4(),
        client_id=client_id,
        invoice_id=data.invoice_id,
        transaction_id=data.transaction_id,
        confidence_score=Decimal("100"),  # Manual = 100% confidence
        matched_amount=matched_amount,
        is_confirmed=True,
        match_method="manual",
        notes=data.notes,
    )
    db.add(match)

    # Update recon_status
    invoice.recon_status = "matched"
    transaction.recon_status = "matched"

    await db.flush()
    await db.refresh(match)

    return _build_match_response(match, invoice, transaction)


@router.get("/matches/{match_id}", response_model=ReconciliationMatchResponse)
async def get_match(
    client_id: uuid.UUID,
    match_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get match detail."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(ReconciliationMatch).where(
            ReconciliationMatch.id == match_id,
            ReconciliationMatch.client_id == client_id,
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    inv_result = await db.execute(select(Invoice).where(Invoice.id == match.invoice_id))
    invoice = inv_result.scalar_one()
    txn_result = await db.execute(select(Transaction).where(Transaction.id == match.transaction_id))
    transaction = txn_result.scalar_one()

    return _build_match_response(match, invoice, transaction)


@router.put("/matches/{match_id}", response_model=ReconciliationMatchResponse)
async def update_match(
    client_id: uuid.UUID,
    match_id: uuid.UUID,
    data: ReconciliationMatchUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm or update a match."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(ReconciliationMatch).where(
            ReconciliationMatch.id == match_id,
            ReconciliationMatch.client_id == client_id,
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(match, field, value)

    match.updated_at = datetime.now(timezone.utc)

    # If confirming, update recon_status on both sides
    if data.is_confirmed is True:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == match.invoice_id))
        invoice = inv_result.scalar_one()
        invoice.recon_status = "matched"

        txn_result = await db.execute(select(Transaction).where(Transaction.id == match.transaction_id))
        transaction = txn_result.scalar_one()
        transaction.recon_status = "matched"
    else:
        # Load for response
        inv_result = await db.execute(select(Invoice).where(Invoice.id == match.invoice_id))
        invoice = inv_result.scalar_one()
        txn_result = await db.execute(select(Transaction).where(Transaction.id == match.transaction_id))
        transaction = txn_result.scalar_one()

    return _build_match_response(match, invoice, transaction)


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    client_id: uuid.UUID,
    match_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a match and reset recon_status on both sides."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(ReconciliationMatch).where(
            ReconciliationMatch.id == match_id,
            ReconciliationMatch.client_id == client_id,
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    invoice_id = match.invoice_id
    transaction_id = match.transaction_id

    await db.delete(match)

    # Check if invoice has any other confirmed matches
    remaining_inv = await db.execute(
        select(func.count()).select_from(ReconciliationMatch).where(
            ReconciliationMatch.invoice_id == invoice_id,
            ReconciliationMatch.id != match_id,
            ReconciliationMatch.is_confirmed == True,
        )
    )
    if remaining_inv.scalar() == 0:
        inv_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = inv_result.scalar_one_or_none()
        if invoice:
            invoice.recon_status = "unmatched"

    # Check if transaction has any other confirmed matches
    remaining_txn = await db.execute(
        select(func.count()).select_from(ReconciliationMatch).where(
            ReconciliationMatch.transaction_id == transaction_id,
            ReconciliationMatch.id != match_id,
            ReconciliationMatch.is_confirmed == True,
        )
    )
    if remaining_txn.scalar() == 0:
        txn_result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
        txn = txn_result.scalar_one_or_none()
        if txn:
            txn.recon_status = "unmatched"
