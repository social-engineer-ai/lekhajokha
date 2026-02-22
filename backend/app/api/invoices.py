import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.job import Job
from app.schemas.invoice import InvoiceDetailResponse, InvoiceResponse, InvoiceUpdate
from app.schemas.job import JobResponse
from app.services.storage_service import make_invoice_key, upload_file
from app.services.invoice_service import process_invoice

router = APIRouter(prefix="/clients/{client_id}/invoices", tags=["invoices"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_FILES = 20


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


def _get_file_ext(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def _get_content_type(ext: str) -> str:
    content_types = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    return content_types.get(ext, "application/octet-stream")


@router.post("/", response_model=list[JobResponse], status_code=status.HTTP_201_CREATED)
async def upload_invoices(
    client_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    invoice_type: str = Form("auto"),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more invoice files (PDF/JPG/PNG) for OCR processing.
    Each file creates its own Invoice + Job. Returns list of Jobs.
    """
    await _verify_client_ownership(client_id, current_user, db)

    if len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES} files per upload")

    if invoice_type not in ("auto", "sales", "purchase"):
        raise HTTPException(status_code=400, detail="invoice_type must be 'auto', 'sales', or 'purchase'")

    jobs = []

    for file in files:
        filename = file.filename or "invoice.pdf"
        ext = _get_file_ext(filename)

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File '{filename}': unsupported type. Allowed: PDF, JPG, PNG",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail=f"File '{filename}' is empty")
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File '{filename}' exceeds 20MB limit")

        # Create invoice record
        invoice_id = uuid.uuid4()
        file_key = make_invoice_key(str(client_id), str(invoice_id), filename)

        # Upload to MinIO
        upload_file(file_bytes, file_key, content_type=_get_content_type(ext))

        invoice = Invoice(
            id=invoice_id,
            client_id=client_id,
            invoice_type=invoice_type,
            file_path=file_key,
            file_name=filename,
            file_size_bytes=len(file_bytes),
            processing_status="pending",
        )
        db.add(invoice)

        # Create job for tracking
        job = Job(
            id=uuid.uuid4(),
            client_id=client_id,
            job_type="invoice_ocr",
            status="pending",
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)

        # Schedule background processing
        background_tasks.add_task(process_invoice, invoice.id, job.id)
        jobs.append(job)

    return jobs


@router.get("/", response_model=list[InvoiceResponse])
async def list_invoices(
    client_id: uuid.UUID,
    invoice_type: str | None = Query(None),
    processing_status: str | None = Query(None, alias="status"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List invoices for a client with filters."""
    await _verify_client_ownership(client_id, current_user, db)

    query = select(Invoice).where(
        Invoice.client_id == client_id,
        Invoice.is_active == True,
    )

    if invoice_type:
        query = query.where(Invoice.invoice_type == invoice_type)
    if processing_status:
        query = query.where(Invoice.processing_status == processing_status)
    if date_from:
        query = query.where(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.where(Invoice.invoice_date <= date_to)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            Invoice.invoice_number.ilike(search_filter)
            | Invoice.seller_name.ilike(search_filter)
            | Invoice.buyer_name.ilike(search_filter)
            | Invoice.seller_gstin.ilike(search_filter)
            | Invoice.buyer_gstin.ilike(search_filter)
        )

    query = query.order_by(Invoice.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
async def get_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get invoice detail with line items."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client_id,
            Invoice.is_active == True,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    data: InvoiceUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually correct OCR-extracted fields."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client_id,
            Invoice.is_active == True,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(invoice, field, value)

    invoice.updated_at = datetime.now(timezone.utc)
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    client_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an invoice."""
    await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client_id,
            Invoice.is_active == True,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.is_active = False
    invoice.updated_at = datetime.now(timezone.utc)
