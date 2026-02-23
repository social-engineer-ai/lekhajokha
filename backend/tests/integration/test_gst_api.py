"""Integration tests for GST API endpoints (GSTR-1, GSTR-3B, summary)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice


async def _seed_invoices(db: AsyncSession, client_id: uuid.UUID):
    """Create sample sales and purchase invoices for GST computation."""
    sales = Invoice(
        id=uuid.uuid4(), client_id=client_id,
        invoice_type="sales", file_path="s.pdf", file_name="s.pdf",
        file_size_bytes=1024, processing_status="completed",
        invoice_number="S-001", invoice_date=date(2024, 3, 10),
        seller_name="Acme", seller_gstin="27AABCU9603R1ZM",
        buyer_name="Beta Corp", buyer_gstin="07AAACR5055K1Z5",
        place_of_supply="Delhi (07)",
        taxable_amount=Decimal("100000"), igst_amount=Decimal("18000"),
        total_amount=Decimal("118000"),
    )
    purchase = Invoice(
        id=uuid.uuid4(), client_id=client_id,
        invoice_type="purchase", file_path="p.pdf", file_name="p.pdf",
        file_size_bytes=1024, processing_status="completed",
        invoice_number="P-001", invoice_date=date(2024, 3, 12),
        seller_name="Vendor Co", seller_gstin="24AABCV1234R1ZM",
        buyer_name="Acme", buyer_gstin="27AABCU9603R1ZM",
        place_of_supply="Maharashtra (27)",
        taxable_amount=Decimal("50000"), cgst_amount=Decimal("4500"),
        sgst_amount=Decimal("4500"), total_amount=Decimal("59000"),
    )
    db.add_all([sales, purchase])
    await db.flush()


class TestGSTSummary:
    async def test_summary_empty(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/gst/summary?month=3&year=2024", headers=auth_headers)
        assert resp.status_code == 200


class TestGSTR1:
    async def test_gstr1(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_invoices(db_session, uuid.UUID(cid))
        resp = await client.post(
            f"/api/v1/clients/{cid}/gst/gstr1",
            json={"month": 3, "year": 2024},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_gstr1_export(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_invoices(db_session, uuid.UUID(cid))
        resp = await client.post(
            f"/api/v1/clients/{cid}/gst/gstr1/export",
            json={"month": 3, "year": 2024},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")


class TestGSTR3B:
    async def test_gstr3b(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_invoices(db_session, uuid.UUID(cid))
        resp = await client.post(
            f"/api/v1/clients/{cid}/gst/gstr3b",
            json={"month": 3, "year": 2024},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_gstr3b_export(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict, db_session: AsyncSession
    ):
        cid = test_client_entity["id"]
        await _seed_invoices(db_session, uuid.UUID(cid))
        resp = await client.post(
            f"/api/v1/clients/{cid}/gst/gstr3b/export",
            json={"month": 3, "year": 2024},
            headers=auth_headers,
        )
        assert resp.status_code == 200
