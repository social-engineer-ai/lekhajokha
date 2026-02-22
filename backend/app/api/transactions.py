import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.transaction import Transaction
from app.schemas.bank_statement import TransactionResponse, TransactionUpdate

router = APIRouter(prefix="/clients/{client_id}/transactions", tags=["transactions"])


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


@router.get("/", response_model=list[TransactionResponse])
async def list_transactions(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    transaction_type: str | None = None,
    transaction_mode: str | None = None,
    category: str | None = None,
    recon_status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions for a client with filters and pagination."""
    await _verify_client_ownership(client_id, current_user, db)

    query = select(Transaction).where(Transaction.client_id == client_id)

    if bank_account_id:
        query = query.where(Transaction.bank_account_id == bank_account_id)
    if date_from:
        query = query.where(Transaction.transaction_date >= date_from)
    if date_to:
        query = query.where(Transaction.transaction_date <= date_to)
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
    if transaction_mode:
        query = query.where(Transaction.transaction_mode == transaction_mode)
    if category:
        query = query.where(Transaction.category == category)
    if recon_status:
        query = query.where(Transaction.recon_status == recon_status)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Transaction.raw_description.ilike(search_filter),
                Transaction.parsed_counterparty.ilike(search_filter),
                Transaction.reference_number.ilike(search_filter),
            )
        )

    query = query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    client_id: uuid.UUID,
    transaction_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single transaction."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.client_id == client_id,
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    client_id: uuid.UUID,
    transaction_id: uuid.UUID,
    req: TransactionUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction's category or recon status."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.client_id == client_id,
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(txn, field, value)

    await db.flush()
    await db.refresh(txn)
    return txn
