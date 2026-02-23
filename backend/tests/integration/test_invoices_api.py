"""Integration tests for invoice API endpoints."""

import uuid
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice


async def _seed_invoice(db: AsyncSession, client_id: uuid.UUID) -> Invoice:
    inv = Invoice(
        id=uuid.uuid4(), client_id=client_id,
        invoice_type="sales", file_path="test.pdf", file_name="test.pdf",
        file_size_bytes=1024, processing_status="completed",
        invoice_number="INV-TEST-001", invoice_date=date(2024, 3, 15),
        seller_name="Acme", buyer_name="Beta",
        total_amount=Decimal("10000.00"),
    )
    db.add(inv)
    await db.flush()
    return inv


class TestInvoiceList:
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/invoices/", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_with_data(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_invoice(db_session, uuid.UUID(cid))
        resp = await client.get(f"/api/v1/clients/{cid}/invoices/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestInvoiceDetail:
    async def test_get_invoice_detail(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv = await _seed_invoice(db_session, uuid.UUID(cid))
        resp = await client.get(f"/api/v1/clients/{cid}/invoices/{inv.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["invoice_number"] == "INV-TEST-001"


class TestInvoiceUpdate:
    async def test_update_invoice_fields(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        inv = await _seed_invoice(db_session, uuid.UUID(cid))
        resp = await client.put(
            f"/api/v1/clients/{cid}/invoices/{inv.id}",
            json={"invoice_number": "INV-UPDATED"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["invoice_number"] == "INV-UPDATED"

    async def test_update_nonexistent_404(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.put(
            f"/api/v1/clients/{cid}/invoices/{uuid.uuid4()}",
            json={"invoice_number": "X"},
            headers=auth_headers,
        )
        assert resp.status_code == 404
