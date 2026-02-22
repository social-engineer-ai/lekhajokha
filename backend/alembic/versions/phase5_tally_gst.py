"""add tally_configs table, clients.tally_sync_scope, invoices.tally_sync_status

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tally_configs table
    op.create_table(
        "tally_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("accountant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accountants.id"), nullable=False),
        sa.Column("tally_host", sa.String(255), server_default="http://localhost"),
        sa.Column("tally_port", sa.Integer, server_default="9000"),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("is_connected", sa.Boolean, server_default=sa.text("false")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("accountant_id", name="uq_tally_config_accountant"),
    )

    # Add tally_sync_scope to clients table
    op.add_column(
        "clients",
        sa.Column("tally_sync_scope", sa.String(30), server_default="invoices_and_reconciled"),
    )

    # Add tally_sync_status to invoices table
    op.add_column(
        "invoices",
        sa.Column("tally_sync_status", sa.String(20), server_default="pending"),
    )


def downgrade() -> None:
    op.drop_column("invoices", "tally_sync_status")
    op.drop_column("clients", "tally_sync_scope")
    op.drop_table("tally_configs")
