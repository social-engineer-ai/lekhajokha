"""add invoices and invoice_line_items tables

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("invoice_type", sa.String(20), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=True),
        sa.Column("invoice_date", sa.Date, nullable=True),
        sa.Column("seller_name", sa.String(255), nullable=True),
        sa.Column("seller_gstin", sa.String(15), nullable=True),
        sa.Column("buyer_name", sa.String(255), nullable=True),
        sa.Column("buyer_gstin", sa.String(15), nullable=True),
        sa.Column("place_of_supply", sa.String(100), nullable=True),
        sa.Column("taxable_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("cgst_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("sgst_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("igst_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_tax", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("raw_ocr_text", sa.Text, nullable=True),
        sa.Column("processing_status", sa.String(20), server_default="pending"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("ocr_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"])

    op.create_table(
        "invoice_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("line_number", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("hsn_sac_code", sa.String(10), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("gst_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("cgst_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("sgst_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("igst_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
