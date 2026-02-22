"""add reconciliation_matches table and invoices.recon_status

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add recon_status to invoices table
    op.add_column(
        "invoices",
        sa.Column("recon_status", sa.String(20), server_default="unmatched"),
    )

    # Create reconciliation_matches table
    op.create_table(
        "reconciliation_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("matched_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("is_confirmed", sa.Boolean, server_default=sa.text("false")),
        sa.Column("match_method", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("invoice_id", "transaction_id", name="uq_match_invoice_transaction"),
    )
    op.create_index("ix_reconciliation_matches_client_id", "reconciliation_matches", ["client_id"])
    op.create_index("ix_reconciliation_matches_invoice_id", "reconciliation_matches", ["invoice_id"])
    op.create_index("ix_reconciliation_matches_transaction_id", "reconciliation_matches", ["transaction_id"])


def downgrade() -> None:
    op.drop_table("reconciliation_matches")
    op.drop_column("invoices", "recon_status")
