"""Integration tests for reconciliation API endpoints."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_account import BankAccount
from app.models.bank_statement import BankStatement
from app.models.invoice import Invoice
from app.models.transaction import Transaction


async def _seed_invoice_and_transaction(db: AsyncSession, client_id: uuid.UUID) -> tuple[Invoice, Transaction]:
    """Create an invoice and a matching transaction for reconciliation tests."""
    # Bank account → statement → transaction chain
    acct = BankAccount(
        id=uuid.uuid4(), client_id=client_id,
        bank_name="HDFC", account_number="123456", ifsc_code="HDFC0001234",
        account_type="current",
    )
    db.add(acct)
    await db.flush()

    stmt = BankStatement(
        id=uuid.uuid4(), client_id=client_id, bank_account_id=acct.id,
        file_path="test.pdf", file_name="test.pdf", file_size_bytes=1024,
        processing_status="completed",
    )
    db.add(stmt)
    await db.flush()

    txn = Transaction(
        id=uuid.uuid4(), client_id=client_id,
        bank_statement_id=stmt.id, bank_account_id=acct.id,
        transaction_date=date(2024, 3, 15),
        raw_description="NEFT/ICIC0001234/BETA CORP/REF123",
        amount=Decimal("59000.00"), transaction_type="credit",
    )
    db.add(txn)

    inv = Invoice(
        id=uuid.uuid4(), client_id=client_id,
        invoice_type="sales", file_path="inv.pdf", file_name="inv.pdf",
        file_size_bytes=2048, processing_status="completed",
        invoice_number="INV-001", invoice_date=date(2024, 3, 15),
        seller_name="Acme", buyer_name="Beta Corp",
        total_amount=Decimal("59000.00"), recon_status="unmatched",
    )
    db.add(inv)
    await db.flush()
    return inv, txn


class TestReconciliationRun:
    async def test_trigger_reconciliation_creates_job(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict
    ):
        cid = test_client_entity["id"]
        resp = await client.post(f"/api/v1/clients/{cid}/reconciliation/run", headers=auth_headers)
        assert resp.status_code == 202
        data = resp.json()
        assert data["job_type"] == "reconciliation"
        assert data["status"] == "pending"


class TestReconciliationSummary:
    async def test_empty_summary(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/reconciliation/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoices"] == 0
        assert data["total_transactions"] == 0

    async def test_summary_with_data(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_invoice_and_transaction(db_session, uuid.UUID(cid))
        resp = await client.get(f"/api/v1/clients/{cid}/reconciliation/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_invoices"] == 1
        assert data["total_transactions"] == 1
        assert data["unmatched_invoices"] == 1


class TestManualMatch:
    async def test_create_and_get_manual_match(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv, txn = await _seed_invoice_and_transaction(db_session, uuid.UUID(cid))

        resp = await client.post(
            f"/api/v1/clients/{cid}/reconciliation/matches",
            json={"invoice_id": str(inv.id), "transaction_id": str(txn.id), "notes": "Manual check"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        match_data = resp.json()
        assert match_data["match_method"] == "manual"
        assert match_data["is_confirmed"] is True

        # Get by ID
        match_id = match_data["id"]
        resp2 = await client.get(f"/api/v1/clients/{cid}/reconciliation/matches/{match_id}", headers=auth_headers)
        assert resp2.status_code == 200

    async def test_duplicate_match_409(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv, txn = await _seed_invoice_and_transaction(db_session, uuid.UUID(cid))
        payload = {"invoice_id": str(inv.id), "transaction_id": str(txn.id)}
        await client.post(f"/api/v1/clients/{cid}/reconciliation/matches", json=payload, headers=auth_headers)
        resp = await client.post(f"/api/v1/clients/{cid}/reconciliation/matches", json=payload, headers=auth_headers)
        assert resp.status_code == 409

    async def test_list_matches(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv, txn = await _seed_invoice_and_transaction(db_session, uuid.UUID(cid))
        await client.post(
            f"/api/v1/clients/{cid}/reconciliation/matches",
            json={"invoice_id": str(inv.id), "transaction_id": str(txn.id)},
            headers=auth_headers,
        )
        resp = await client.get(f"/api/v1/clients/{cid}/reconciliation/matches", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_update_match(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv, txn = await _seed_invoice_and_transaction(db_session, uuid.UUID(cid))
        create_resp = await client.post(
            f"/api/v1/clients/{cid}/reconciliation/matches",
            json={"invoice_id": str(inv.id), "transaction_id": str(txn.id)},
            headers=auth_headers,
        )
        match_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/v1/clients/{cid}/reconciliation/matches/{match_id}",
            json={"notes": "Updated notes"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Updated notes"

    async def test_delete_match(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv, txn = await _seed_invoice_and_transaction(db_session, uuid.UUID(cid))
        create_resp = await client.post(
            f"/api/v1/clients/{cid}/reconciliation/matches",
            json={"invoice_id": str(inv.id), "transaction_id": str(txn.id)},
            headers=auth_headers,
        )
        match_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/clients/{cid}/reconciliation/matches/{match_id}", headers=auth_headers)
        assert resp.status_code == 204
