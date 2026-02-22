import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.invoice_line_item import InvoiceLineItem
from app.models.job import Job
from app.services.storage_service import download_file
from app.services.vision_service import extract_text_from_pdf, extract_text_from_image
from app.services.invoice_parser import parse_invoice_text, detect_invoice_type

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}


async def process_invoice(invoice_id: uuid.UUID, job_id: uuid.UUID):
    """Background task: download file → OCR → parse fields → save to DB.
    Uses its own DB session (not the request's session).
    """
    async with async_session() as db:
        try:
            # Load invoice and job
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            if not invoice:
                logger.error(f"Invoice {invoice_id} not found")
                return

            result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Mark as processing
            invoice.processing_status = "processing"
            job.status = "processing"
            await db.commit()

            # Download file from MinIO
            file_bytes = download_file(invoice.file_path)

            # Detect file type from extension
            file_ext = "." + invoice.file_name.rsplit(".", 1)[-1].lower() if "." in invoice.file_name else ""

            # Call OCR
            if file_ext in PDF_EXTENSIONS:
                ocr_text, confidence = extract_text_from_pdf(file_bytes)
            elif file_ext in IMAGE_EXTENSIONS:
                ocr_text, confidence = extract_text_from_image(file_bytes)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            if not ocr_text.strip():
                invoice.processing_status = "failed"
                invoice.processing_error = "OCR extracted no text from the file."
                job.status = "failed"
                job.error_message = invoice.processing_error
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Save raw OCR text
            invoice.raw_ocr_text = ocr_text
            invoice.ocr_confidence = confidence

            # Parse structured fields
            parsed = parse_invoice_text(ocr_text)

            # Load client to get GSTIN for sales/purchase detection
            result = await db.execute(
                select(Client).where(Client.id == invoice.client_id)
            )
            client = result.scalar_one_or_none()
            client_gstin = client.gstin if client else None

            # Auto-detect invoice type if set to "auto"
            if invoice.invoice_type == "auto":
                invoice.invoice_type = detect_invoice_type(parsed.seller_gstin, client_gstin)

            # Update invoice fields
            invoice.invoice_number = parsed.invoice_number
            invoice.invoice_date = parsed.invoice_date
            invoice.seller_name = parsed.seller_name
            invoice.seller_gstin = parsed.seller_gstin
            invoice.buyer_name = parsed.buyer_name
            invoice.buyer_gstin = parsed.buyer_gstin
            invoice.place_of_supply = parsed.place_of_supply
            invoice.taxable_amount = parsed.taxable_amount
            invoice.cgst_amount = parsed.cgst_amount
            invoice.sgst_amount = parsed.sgst_amount
            invoice.igst_amount = parsed.igst_amount
            invoice.total_tax = parsed.total_tax
            invoice.total_amount = parsed.total_amount

            # Batch create line items
            line_item_models = []
            for item in parsed.line_items:
                li = InvoiceLineItem(
                    id=uuid.uuid4(),
                    invoice_id=invoice.id,
                    line_number=item.line_number,
                    description=item.description,
                    hsn_sac_code=item.hsn_sac_code,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    amount=item.amount,
                    gst_rate=item.gst_rate,
                    cgst_amount=None,
                    sgst_amount=None,
                    igst_amount=None,
                )
                line_item_models.append(li)

            db.add_all(line_item_models)

            # Update status
            invoice.processing_status = "completed"
            invoice.processing_error = None

            job.status = "completed"
            job.result_summary = f"Extracted {len(line_item_models)} line items, invoice #{parsed.invoice_number or 'N/A'}"
            job.completed_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(f"Invoice {invoice_id}: processed with {len(line_item_models)} line items")

        except Exception as e:
            logger.exception(f"Error processing invoice {invoice_id}: {e}")
            await db.rollback()
            # Try to mark as failed in a separate session
            try:
                async with async_session() as err_db:
                    result = await err_db.execute(
                        select(Invoice).where(Invoice.id == invoice_id)
                    )
                    inv = result.scalar_one_or_none()
                    if inv:
                        inv.processing_status = "failed"
                        inv.processing_error = str(e)[:500]

                    result = await err_db.execute(
                        select(Job).where(Job.id == job_id)
                    )
                    j = result.scalar_one_or_none()
                    if j:
                        j.status = "failed"
                        j.error_message = str(e)[:500]
                        j.completed_at = datetime.now(timezone.utc)

                    await err_db.commit()
            except Exception:
                logger.exception("Failed to update error status")
