import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.bank_account import BankAccount
from app.models.bank_statement import BankStatement
from app.models.client import Client
from app.models.job import Job
from app.schemas.bank_statement import BankStatementDetailResponse, BankStatementResponse
from app.schemas.job import JobResponse
from app.services.parsers.pdf_utils import is_pdf_encrypted, decrypt_pdf
from app.services.storage_service import make_statement_key, upload_file
from app.services.statement_service import process_statement

router = APIRouter(prefix="/clients/{client_id}/bank-statements", tags=["bank-statements"])


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


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def upload_bank_statement(
    client_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    bank_account_id: uuid.UUID = Form(...),
    password: str | None = Form(None),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a bank statement PDF for parsing."""
    await _verify_client_ownership(client_id, current_user, db)

    # Verify bank account belongs to this client
    result = await db.execute(
        select(BankAccount).where(
            BankAccount.id == bank_account_id,
            BankAccount.client_id == client_id,
            BankAccount.is_active == True,
        )
    )
    bank_account = result.scalar_one_or_none()
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Read file
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(pdf_bytes) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    # Check encryption and handle password
    is_encrypted = is_pdf_encrypted(pdf_bytes)
    if is_encrypted:
        if not password:
            raise HTTPException(
                status_code=400,
                detail="PDF is password-protected. Please provide the password.",
            )
        try:
            pdf_bytes = decrypt_pdf(pdf_bytes, password)
        except Exception:
            raise HTTPException(status_code=400, detail="Incorrect PDF password")

    # Create statement record
    statement_id = uuid.uuid4()
    file_key = make_statement_key(str(client_id), str(statement_id), file.filename or "statement.pdf")

    # Upload decrypted PDF to MinIO
    upload_file(pdf_bytes, file_key)

    statement = BankStatement(
        id=statement_id,
        bank_account_id=bank_account_id,
        client_id=client_id,
        file_path=file_key,
        file_name=file.filename or "statement.pdf",
        file_size_bytes=len(pdf_bytes),
        is_password_protected=is_encrypted,
        processing_status="pending",
    )
    db.add(statement)

    # Create job for tracking
    job = Job(
        id=uuid.uuid4(),
        client_id=client_id,
        job_type="bank_import",
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.refresh(statement)
    await db.refresh(job)

    # Schedule background processing
    background_tasks.add_task(process_statement, statement.id, job.id)

    return job


@router.get("/", response_model=list[BankStatementResponse])
async def list_bank_statements(
    client_id: uuid.UUID,
    bank_account_id: uuid.UUID | None = None,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all bank statements for a client, optionally filtered by bank account."""
    await _verify_client_ownership(client_id, current_user, db)

    query = select(BankStatement).where(BankStatement.client_id == client_id)
    if bank_account_id:
        query = query.where(BankStatement.bank_account_id == bank_account_id)
    query = query.order_by(BankStatement.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{statement_id}", response_model=BankStatementDetailResponse)
async def get_bank_statement(
    client_id: uuid.UUID,
    statement_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single bank statement with its transactions."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(BankStatement).where(
            BankStatement.id == statement_id,
            BankStatement.client_id == client_id,
        )
    )
    statement = result.scalar_one_or_none()
    if not statement:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    return statement
