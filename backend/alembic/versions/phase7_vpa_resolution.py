"""add vpa_entries table, transactions.vpa_entry_id, messages.whatsapp_profile_name

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Seed templates for VPA collection request
SEED_TEMPLATES = [
    {
        "trigger_event": "vpa_collection_request",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": (
            "Hi {{client_name}}, we need your help identifying {{unresolved_count}} UPI payment(s). "
            "Could you share the VPA/UPI IDs for: {{vendor_list}}? — {{firm_name}}"
        ),
    },
    {
        "trigger_event": "vpa_collection_request",
        "channel": "email",
        "subject_template": "Action needed: UPI VPA verification — {{client_name}}",
        "body_template": (
            "Hi {{client_name}},\n\n"
            "We are verifying UPI VPA details for your account. "
            "Could you help us identify the following {{unresolved_count}} UPI payment(s)?\n\n"
            "{{vendor_list}}\n\n"
            "Please reply with the correct VPA/UPI IDs for each vendor listed above.\n\n"
            "Regards,\n{{firm_name}}"
        ),
    },
]


def upgrade() -> None:
    # Create vpa_entries table
    op.create_table(
        "vpa_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("vpa", sa.String(255), nullable=False, index=True),
        sa.Column("resolved_name", sa.String(255), nullable=True),
        sa.Column("gstin", sa.String(15), nullable=True),
        sa.Column("pan", sa.String(10), nullable=True),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), server_default="0"),
        sa.Column("is_verified", sa.Boolean, server_default=sa.text("false")),
        sa.Column("transaction_count", sa.Integer, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "vpa", name="uq_vpa_entry_client_vpa"),
    )

    # Add vpa_entry_id column to transactions
    op.add_column(
        "transactions",
        sa.Column("vpa_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vpa_entries.id"), nullable=True),
    )
    op.create_index("ix_transactions_vpa_entry_id", "transactions", ["vpa_entry_id"])

    # Add whatsapp_profile_name column to messages
    op.add_column(
        "messages",
        sa.Column("whatsapp_profile_name", sa.String(255), nullable=True),
    )

    # Seed vpa_collection_request templates (system defaults, accountant_id = NULL)
    templates_table = sa.table(
        "message_templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("accountant_id", postgresql.UUID(as_uuid=True)),
        sa.column("trigger_event", sa.String),
        sa.column("channel", sa.String),
        sa.column("subject_template", sa.String),
        sa.column("body_template", sa.Text),
        sa.column("is_active", sa.Boolean),
    )

    op.bulk_insert(templates_table, [
        {
            "id": str(uuid.uuid4()),
            "accountant_id": None,
            "trigger_event": t["trigger_event"],
            "channel": t["channel"],
            "subject_template": t["subject_template"],
            "body_template": t["body_template"],
            "is_active": True,
        }
        for t in SEED_TEMPLATES
    ])


def downgrade() -> None:
    op.drop_index("ix_transactions_vpa_entry_id", table_name="transactions")
    op.drop_column("transactions", "vpa_entry_id")
    op.drop_column("messages", "whatsapp_profile_name")

    # Remove seed templates
    op.execute("DELETE FROM message_templates WHERE trigger_event = 'vpa_collection_request' AND accountant_id IS NULL")

    op.drop_table("vpa_entries")
