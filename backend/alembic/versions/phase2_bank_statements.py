"""add bank_statements and transactions tables

Revision ID: a2b3c4d5e6f7
Revises: 793fea30aae6
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "793fea30aae6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_statements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("is_password_protected", sa.Boolean, default=False),
        sa.Column("period_from", sa.Date, nullable=True),
        sa.Column("period_to", sa.Date, nullable=True),
        sa.Column("processing_status", sa.String(20), default="pending"),
        sa.Column("processing_error", sa.Text, nullable=True),
        sa.Column("transactions_count", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_bank_statements_bank_account_id", "bank_statements", ["bank_account_id"])
    op.create_index("ix_bank_statements_client_id", "bank_statements", ["client_id"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bank_statement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_statements.id"), nullable=False),
        sa.Column("bank_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("transaction_date", sa.Date, nullable=False),
        sa.Column("value_date", sa.Date, nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("cheque_ref_no", sa.String(50), nullable=True),
        sa.Column("raw_description", sa.Text, nullable=False),
        sa.Column("parsed_counterparty", sa.String(255), nullable=True),
        sa.Column("parsed_bank_ifsc", sa.String(11), nullable=True),
        sa.Column("parsed_upi_id", sa.String(255), nullable=True),
        sa.Column("transaction_mode", sa.String(20), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("running_balance", sa.Numeric(15, 2), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("sub_category", sa.String(100), nullable=True),
        sa.Column("recon_status", sa.String(20), default="unmatched"),
        sa.Column("tally_sync_status", sa.String(20), default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_transactions_bank_statement_id", "transactions", ["bank_statement_id"])
    op.create_index("ix_transactions_bank_account_id", "transactions", ["bank_account_id"])
    op.create_index("ix_transactions_client_id", "transactions", ["client_id"])
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])


def downgrade() -> None:
    op.drop_table("transactions")
    op.drop_table("bank_statements")
