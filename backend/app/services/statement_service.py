import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.bank_account import BankAccount
from app.models.bank_statement import BankStatement
from app.models.client import Client
from app.models.job import Job
from app.models.transaction import Transaction
from app.services.storage_service import download_file
from app.services.parsers.pdf_utils import extract_tables, extract_text
from app.services.parsers.bank_detector import detect_bank, detect_bank_from_name
from app.services.parsers import get_parser
from app.services.parsers.description_parser import parse_description

logger = logging.getLogger(__name__)


async def process_statement(statement_id: uuid.UUID, job_id: uuid.UUID):
    """Background task: download PDF from MinIO, detect bank, parse, insert transactions.
    Uses its own DB session (not the request's session).
    """
    async with async_session() as db:
        try:
            # Load statement and related bank account
            result = await db.execute(
                select(BankStatement).where(BankStatement.id == statement_id)
            )
            statement = result.scalar_one_or_none()
            if not statement:
                logger.error(f"Statement {statement_id} not found")
                return

            result = await db.execute(
                select(Job).where(Job.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Mark as processing
            statement.processing_status = "processing"
            job.status = "processing"
            await db.commit()

            # Load bank account for bank_name fallback
            result = await db.execute(
                select(BankAccount).where(BankAccount.id == statement.bank_account_id)
            )
            bank_account = result.scalar_one_or_none()

            # Download PDF from MinIO
            pdf_bytes = download_file(statement.file_path)

            # Extract text for bank detection
            text = extract_text(pdf_bytes)
            bank_key = detect_bank(text)
            if not bank_key and bank_account:
                bank_key = detect_bank_from_name(bank_account.bank_name)

            logger.info(f"Detected bank: {bank_key or 'unknown (using generic)'}")

            # Extract tables
            tables = extract_tables(pdf_bytes)
            if not tables:
                statement.processing_status = "failed"
                statement.processing_error = "No tables found in PDF. The statement format may not be supported."
                job.status = "failed"
                job.error_message = statement.processing_error
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Parse with bank-specific or generic parser
            parser = get_parser(bank_key)
            raw_transactions = parser.parse(tables)

            if not raw_transactions:
                statement.processing_status = "failed"
                statement.processing_error = "Could not parse any transactions from the PDF tables."
                job.status = "failed"
                job.error_message = statement.processing_error
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Determine period from/to
            dates = [t.transaction_date for t in raw_transactions]
            statement.period_from = min(dates)
            statement.period_to = max(dates)

            # Enrich descriptions and batch insert transactions
            transaction_models = []
            for raw_txn in raw_transactions:
                parsed = parse_description(raw_txn.description)
                txn = Transaction(
                    id=uuid.uuid4(),
                    bank_statement_id=statement.id,
                    bank_account_id=statement.bank_account_id,
                    client_id=statement.client_id,
                    transaction_date=raw_txn.transaction_date,
                    value_date=raw_txn.value_date,
                    reference_number=raw_txn.reference_number or parsed.reference,
                    cheque_ref_no=raw_txn.cheque_ref_no,
                    raw_description=raw_txn.description,
                    parsed_counterparty=parsed.counterparty,
                    parsed_bank_ifsc=parsed.bank_ifsc,
                    parsed_upi_id=parsed.upi_id,
                    transaction_mode=parsed.mode,
                    amount=raw_txn.amount,
                    transaction_type=raw_txn.transaction_type,
                    running_balance=raw_txn.running_balance,
                )
                transaction_models.append(txn)

            db.add_all(transaction_models)

            # Update statement metadata
            statement.transactions_count = len(transaction_models)
            statement.processing_status = "completed"
            statement.processing_error = None

            # Update job
            job.status = "completed"
            job.result_summary = f"Parsed {len(transaction_models)} transactions from {bank_key or 'unknown'} bank statement"
            job.completed_at = datetime.now(timezone.utc)

            await db.commit()
            logger.info(
                f"Statement {statement_id}: parsed {len(transaction_models)} transactions"
            )

            # Auto-tag UPI transactions with known VPAs (fire-and-forget)
            try:
                from app.services.vpa_service import tag_transactions_quick
                upi_txns = [t for t in transaction_models if t.parsed_upi_id]
                if upi_txns:
                    await tag_transactions_quick(db, statement.client_id, upi_txns)
            except Exception:
                logger.debug("VPA quick-tagging failed (non-critical)", exc_info=True)

            # Fire notification (fire-and-forget)
            try:
                from app.services.notification_service import notify
                # Load client to get accountant_id
                cl_result = await db.execute(select(Client).where(Client.id == statement.client_id))
                cl = cl_result.scalar_one_or_none()
                if cl:
                    await notify(
                        client_id=statement.client_id,
                        accountant_id=cl.accountant_id,
                        trigger_event="statement_processed",
                        context_data={
                            "bank_name": bank_account.bank_name if bank_account else (bank_key or "Unknown"),
                            "txn_count": str(len(transaction_models)),
                        },
                    )
            except Exception:
                logger.debug("Notification dispatch failed (non-critical)", exc_info=True)

        except Exception as e:
            logger.exception(f"Error processing statement {statement_id}: {e}")
            await db.rollback()
            # Try to mark as failed
            try:
                async with async_session() as err_db:
                    result = await err_db.execute(
                        select(BankStatement).where(BankStatement.id == statement_id)
                    )
                    stmt = result.scalar_one_or_none()
                    if stmt:
                        stmt.processing_status = "failed"
                        stmt.processing_error = str(e)[:500]

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
