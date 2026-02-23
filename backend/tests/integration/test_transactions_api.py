"""Integration tests for transaction API endpoints."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_account import BankAccount
from app.models.bank_statement import BankStatement
from app.models.transaction import Transaction


async def _seed_transaction(db: AsyncSession, client_id: uuid.UUID) -> Transaction:
    acct = BankAccount(
        id=uuid.uuid4(), client_id=client_id,
        bank_name="HDFC", account_number="123456", account_type="current",
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
        raw_description="UPI/412345678/AMIT/amit@ybl",
        amount=Decimal("5000.00"), transaction_type="credit",
        transaction_mode="UPI", parsed_counterparty="AMIT",
    )
    db.add(txn)
    await db.flush()
    return txn


class TestTransactionsAPI:
    async def test_list_transactions_empty(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/transactions/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_with_data(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_transaction(db_session, uuid.UUID(cid))
        resp = await client.get(f"/api/v1/clients/{cid}/transactions/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["transaction_mode"] == "UPI"

    async def test_update_transaction_category(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        txn = await _seed_transaction(db_session, uuid.UUID(cid))
        resp = await client.put(
            f"/api/v1/clients/{cid}/transactions/{txn.id}",
            json={"category": "Sales Receipt"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["category"] == "Sales Receipt"
