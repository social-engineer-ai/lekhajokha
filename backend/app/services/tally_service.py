"""Tally sync and export service."""

import uuid
import logging
from datetime import datetime, timezone
from calendar import monthrange

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.models.reconciliation_match import ReconciliationMatch
from app.models.tally_config import TallyConfig
from app.models.job import Job
from app.services.tally_xml import (
    generate_sales_voucher,
    generate_purchase_voucher,
    generate_payment_voucher,
    generate_receipt_voucher,
    generate_batch_xml,
)

logger = logging.getLogger(__name__)


async def test_tally_connection(host: str, port: int) -> dict:
    """Test connection to Tally by requesting company info."""
    tally_url = f"{host}:{port}"
    request_xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>"
        "<BODY><EXPORTDATA><REQUESTDESC>"
        "<REPORTNAME>List of Companies</REPORTNAME>"
        "</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(tally_url, content=request_xml, headers={"Content-Type": "application/xml"})
            if response.status_code == 200:
                body = response.text
                # Try to extract company name from response
                company_name = None
                if "<COMPANYNAME>" in body:
                    start = body.index("<COMPANYNAME>") + len("<COMPANYNAME>")
                    end = body.index("</COMPANYNAME>", start)
                    company_name = body[start:end].strip()
                return {"connected": True, "company_name": company_name, "error": None}
            else:
                return {"connected": False, "company_name": None, "error": f"Tally returned status {response.status_code}"}
    except httpx.ConnectError:
        return {"connected": False, "company_name": None, "error": "Cannot connect to Tally. Ensure Tally Prime is running."}
    except httpx.TimeoutException:
        return {"connected": False, "company_name": None, "error": "Connection timed out. Check host and port."}
    except Exception as e:
        return {"connected": False, "company_name": None, "error": str(e)[:200]}


async def sync_to_tally(client_id: uuid.UUID, job_id: uuid.UUID):
    """Background task: generate XML for unsynced data and push to Tally API."""
    async with async_session() as db:
        try:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            job.status = "processing"
            await db.commit()

            # Load client
            result = await db.execute(select(Client).where(Client.id == client_id))
            client = result.scalar_one_or_none()
            if not client:
                job.status = "failed"
                job.error_message = "Client not found"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Load tally config for accountant
            result = await db.execute(
                select(TallyConfig).where(TallyConfig.accountant_id == client.accountant_id)
            )
            config = result.scalar_one_or_none()
            if not config:
                job.status = "failed"
                job.error_message = "Tally not configured. Go to Settings."
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            scope = client.tally_sync_scope
            vouchers = []
            synced_invoices = []
            synced_transactions = []

            # Collect unsynced invoices
            result = await db.execute(
                select(Invoice).options(selectinload(Invoice.line_items)).where(
                    Invoice.client_id == client_id,
                    Invoice.is_active == True,
                    Invoice.processing_status == "completed",
                    Invoice.tally_sync_status == "pending",
                )
            )
            invoices = list(result.scalars().all())

            for inv in invoices:
                if inv.invoice_type == "sales":
                    vouchers.append(generate_sales_voucher(inv, client))
                else:
                    vouchers.append(generate_purchase_voucher(inv, client))
                synced_invoices.append(inv)

            # Collect reconciled matches for payment/receipt vouchers
            if scope in ("invoices_and_reconciled", "all"):
                result = await db.execute(
                    select(ReconciliationMatch).where(
                        ReconciliationMatch.client_id == client_id,
                        ReconciliationMatch.is_confirmed == True,
                    )
                )
                matches = list(result.scalars().all())

                for match in matches:
                    inv_r = await db.execute(select(Invoice).where(Invoice.id == match.invoice_id))
                    inv = inv_r.scalar_one_or_none()
                    txn_r = await db.execute(select(Transaction).where(Transaction.id == match.transaction_id))
                    txn = txn_r.scalar_one_or_none()

                    if not inv or not txn:
                        continue
                    if txn.tally_sync_status != "pending":
                        continue

                    if inv.invoice_type == "purchase":
                        vouchers.append(generate_payment_voucher(match, inv, txn))
                    else:
                        vouchers.append(generate_receipt_voucher(match, inv, txn))
                    synced_transactions.append(txn)

            # Collect all remaining transactions if scope is "all"
            if scope == "all":
                already_synced_ids = {t.id for t in synced_transactions}
                result = await db.execute(
                    select(Transaction).where(
                        Transaction.client_id == client_id,
                        Transaction.tally_sync_status == "pending",
                    )
                )
                all_txns = list(result.scalars().all())
                for txn in all_txns:
                    if txn.id in already_synced_ids:
                        continue
                    # Create a generic payment/receipt voucher for unmatched txns
                    # These go as contra entries — simplified
                    synced_transactions.append(txn)

            if not vouchers:
                job.status = "completed"
                job.result_summary = "No new data to sync"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Replace company placeholder
            company = config.company_name or "##COMPANY##"
            vouchers = [v.replace("##COMPANY##", company) for v in vouchers]

            # Generate batch XML
            batch_xml = generate_batch_xml(vouchers)
            batch_xml = batch_xml.replace("##COMPANY##", company)

            # Push to Tally
            tally_url = f"{config.tally_host}:{config.tally_port}"
            try:
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    response = await http_client.post(
                        tally_url, content=batch_xml, headers={"Content-Type": "application/xml"}
                    )
                    if response.status_code != 200:
                        job.status = "failed"
                        job.error_message = f"Tally returned status {response.status_code}"
                        job.completed_at = datetime.now(timezone.utc)
                        await db.commit()
                        return
            except Exception as e:
                job.status = "failed"
                job.error_message = f"Connection to Tally failed: {str(e)[:200]}"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            # Mark synced
            for inv in synced_invoices:
                inv.tally_sync_status = "synced"
            for txn in synced_transactions:
                txn.tally_sync_status = "synced"

            config.last_sync_at = datetime.now(timezone.utc)
            config.is_connected = True

            job.status = "completed"
            job.result_summary = (
                f"Synced {len(synced_invoices)} invoices, {len(synced_transactions)} transactions "
                f"({len(vouchers)} vouchers)"
            )
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(f"Tally sync for client {client_id}: {job.result_summary}")

        except Exception as e:
            logger.exception(f"Error syncing to Tally for client {client_id}: {e}")
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


async def export_tally_xml(
    client_id: uuid.UUID, month: int, year: int, scope: str, db: AsyncSession
) -> str:
    """Generate XML export file (no Tally connection needed)."""
    # Load client
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise ValueError("Client not found")

    # Date range
    _, last_day = monthrange(year, month)
    from datetime import date
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    vouchers = []

    # Invoices in period
    result = await db.execute(
        select(Invoice).options(selectinload(Invoice.line_items)).where(
            Invoice.client_id == client_id,
            Invoice.is_active == True,
            Invoice.processing_status == "completed",
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
        )
    )
    invoices = list(result.scalars().all())

    for inv in invoices:
        if inv.invoice_type == "sales":
            vouchers.append(generate_sales_voucher(inv, client))
        else:
            vouchers.append(generate_purchase_voucher(inv, client))

    # Reconciled matches
    if scope in ("invoices_and_reconciled", "all"):
        result = await db.execute(
            select(ReconciliationMatch).where(
                ReconciliationMatch.client_id == client_id,
                ReconciliationMatch.is_confirmed == True,
            )
        )
        matches = list(result.scalars().all())

        for match in matches:
            inv_r = await db.execute(select(Invoice).where(Invoice.id == match.invoice_id))
            inv = inv_r.scalar_one_or_none()
            txn_r = await db.execute(select(Transaction).where(Transaction.id == match.transaction_id))
            txn = txn_r.scalar_one_or_none()

            if not inv or not txn:
                continue
            if txn.transaction_date < start_date or txn.transaction_date > end_date:
                continue

            if inv.invoice_type == "purchase":
                vouchers.append(generate_payment_voucher(match, inv, txn))
            else:
                vouchers.append(generate_receipt_voucher(match, inv, txn))

    if not vouchers:
        return '<?xml version="1.0" encoding="utf-8"?><ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA></REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>'

    # Load tally config for company name
    result = await db.execute(
        select(TallyConfig).where(TallyConfig.accountant_id == client.accountant_id)
    )
    config = result.scalar_one_or_none()
    company = config.company_name if config and config.company_name else "My Company"

    batch_xml = generate_batch_xml(vouchers)
    return batch_xml.replace("##COMPANY##", company)
