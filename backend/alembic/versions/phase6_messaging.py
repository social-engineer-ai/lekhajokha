"""add messages, message_templates, messaging_configs tables

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-02-22 00:00:00.000000
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Seed templates: 6 triggers x 2 channels = 12
SEED_TEMPLATES = [
    # statement_processed
    {
        "trigger_event": "statement_processed",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": "Hi {{client_name}}, your bank statement for {{bank_name}} has been processed. {{txn_count}} transactions found. — {{firm_name}}",
    },
    {
        "trigger_event": "statement_processed",
        "channel": "email",
        "subject_template": "Bank Statement Processed — {{bank_name}}",
        "body_template": "Hi {{client_name}},\n\nYour bank statement for {{bank_name}} has been processed successfully. We found {{txn_count}} transactions.\n\nPlease log in to LekhaJokha to review.\n\nRegards,\n{{firm_name}}",
    },
    # invoice_ocr_done
    {
        "trigger_event": "invoice_ocr_done",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": "Hi {{client_name}}, {{invoice_count}} invoice(s) processed. Please review on LekhaJokha. — {{firm_name}}",
    },
    {
        "trigger_event": "invoice_ocr_done",
        "channel": "email",
        "subject_template": "Invoice Processing Complete",
        "body_template": "Hi {{client_name}},\n\n{{invoice_count}} invoice(s) have been processed successfully.\n\nPlease log in to LekhaJokha to review the extracted data.\n\nRegards,\n{{firm_name}}",
    },
    # reconciliation_complete
    {
        "trigger_event": "reconciliation_complete",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": "Hi {{client_name}}, reconciliation complete. {{matched_count}} matches found. — {{firm_name}}",
    },
    {
        "trigger_event": "reconciliation_complete",
        "channel": "email",
        "subject_template": "Reconciliation Complete",
        "body_template": "Hi {{client_name}},\n\nReconciliation has been completed. {{matched_count}} matches were found.\n\nPlease log in to LekhaJokha to review.\n\nRegards,\n{{firm_name}}",
    },
    # gst_return_ready
    {
        "trigger_event": "gst_return_ready",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": "Hi {{client_name}}, your {{return_type}} for {{period}} is ready for review. — {{firm_name}}",
    },
    {
        "trigger_event": "gst_return_ready",
        "channel": "email",
        "subject_template": "{{return_type}} Ready — {{period}}",
        "body_template": "Hi {{client_name}},\n\nYour {{return_type}} for the period {{period}} is ready for review.\n\nPlease log in to LekhaJokha to download or verify.\n\nRegards,\n{{firm_name}}",
    },
    # tally_sync_done
    {
        "trigger_event": "tally_sync_done",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": "Hi {{client_name}}, Tally sync completed. {{voucher_count}} vouchers synced. — {{firm_name}}",
    },
    {
        "trigger_event": "tally_sync_done",
        "channel": "email",
        "subject_template": "Tally Sync Complete",
        "body_template": "Hi {{client_name}},\n\nTally sync has been completed successfully. {{voucher_count}} vouchers were synced.\n\nRegards,\n{{firm_name}}",
    },
    # payment_reminder
    {
        "trigger_event": "payment_reminder",
        "channel": "whatsapp",
        "subject_template": None,
        "body_template": "Hi {{client_name}}, reminder: pending payment of ₹{{amount}} for invoice {{invoice_number}}. — {{firm_name}}",
    },
    {
        "trigger_event": "payment_reminder",
        "channel": "email",
        "subject_template": "Payment Reminder — Invoice {{invoice_number}}",
        "body_template": "Hi {{client_name}},\n\nThis is a reminder regarding a pending payment of ₹{{amount}} for invoice {{invoice_number}}.\n\nPlease arrange the payment at the earliest.\n\nRegards,\n{{firm_name}}",
    },
]


def upgrade() -> None:
    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False, index=True),
        sa.Column("accountant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accountants.id"), nullable=False, index=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("message_type", sa.String(20), server_default="text"),
        sa.Column("attachment_path", sa.String(500), nullable=True),
        sa.Column("attachment_name", sa.String(255), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("triggered_by", sa.String(50), server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create message_templates table
    op.create_table(
        "message_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("accountant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accountants.id"), nullable=True, index=True),
        sa.Column("trigger_event", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject_template", sa.String(500), nullable=True),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("accountant_id", "trigger_event", "channel", name="uq_template_accountant_trigger_channel"),
    )

    # Create messaging_configs table
    op.create_table(
        "messaging_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("accountant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accountants.id"), nullable=False),
        sa.Column("whatsapp_enabled", sa.Boolean, server_default=sa.text("false")),
        sa.Column("email_enabled", sa.Boolean, server_default=sa.text("false")),
        sa.Column("twilio_account_sid", sa.String(255), nullable=True),
        sa.Column("twilio_auth_token", sa.String(255), nullable=True),
        sa.Column("twilio_whatsapp_number", sa.String(20), nullable=True),
        sa.Column("smtp_host", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer, server_default="587"),
        sa.Column("smtp_username", sa.String(255), nullable=True),
        sa.Column("smtp_password", sa.String(255), nullable=True),
        sa.Column("smtp_from_email", sa.String(255), nullable=True),
        sa.Column("smtp_use_tls", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("accountant_id", name="uq_messaging_config_accountant"),
    )

    # Seed system default templates (accountant_id = NULL)
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
    op.drop_table("messaging_configs")
    op.drop_table("message_templates")
    op.drop_table("messages")
