import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.bank_account import BankAccount
from app.models.client import Client
from app.schemas.client import BankAccountCreate, BankAccountResponse, BankAccountUpdate

router = APIRouter(prefix="/clients/{client_id}/bank-accounts", tags=["bank-accounts"])


async def _verify_client_ownership(
    client_id: uuid.UUID, current_user: Accountant, db: AsyncSession
) -> Client:
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.accountant_id == current_user.id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/", response_model=list[BankAccountResponse])
async def list_bank_accounts(
    client_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_client_ownership(client_id, current_user, db)
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.client_id == client_id,
            BankAccount.is_active == True,
        )
    )
    return result.scalars().all()


@router.post("/", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    client_id: uuid.UUID,
    req: BankAccountCreate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_client_ownership(client_id, current_user, db)

    # If marked as primary, unset other primaries
    if req.is_primary:
        existing = await db.execute(
            select(BankAccount).where(
                BankAccount.client_id == client_id,
                BankAccount.is_primary == True,
            )
        )
        for acct in existing.scalars().all():
            acct.is_primary = False

    bank_account = BankAccount(
        id=uuid.uuid4(),
        client_id=client_id,
        bank_name=req.bank_name,
        account_number=req.account_number,
        ifsc_code=req.ifsc_code,
        branch_name=req.branch_name,
        account_type=req.account_type,
        is_primary=req.is_primary,
    )
    db.add(bank_account)
    await db.flush()
    await db.refresh(bank_account)
    return bank_account


@router.get("/{account_id}", response_model=BankAccountResponse)
async def get_bank_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_client_ownership(client_id, current_user, db)
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return account


@router.put("/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    req: BankAccountUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_client_ownership(client_id, current_user, db)
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    update_data = req.model_dump(exclude_unset=True)

    if update_data.get("is_primary"):
        existing = await db.execute(
            select(BankAccount).where(
                BankAccount.client_id == client_id,
                BankAccount.is_primary == True,
                BankAccount.id != account_id,
            )
        )
        for acct in existing.scalars().all():
            acct.is_primary = False

    for field, value in update_data.items():
        setattr(account, field, value)

    await db.flush()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    client_id: uuid.UUID,
    account_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_client_ownership(client_id, current_user, db)
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == account_id,
            BankAccount.client_id == client_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    account.is_active = False
    await db.flush()
