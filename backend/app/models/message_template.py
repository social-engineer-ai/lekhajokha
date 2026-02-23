import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageTemplate(Base):
    __tablename__ = "message_templates"
    __table_args__ = (
        UniqueConstraint("accountant_id", "trigger_event", "channel", name="uq_template_accountant_trigger_channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accountant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accountants.id"), nullable=True, index=True
    )  # NULL = system default
    trigger_event: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # statement_processed, invoice_ocr_done, reconciliation_complete, gst_return_ready, tally_sync_done, payment_reminder
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # whatsapp / email
    subject_template: Mapped[str] = mapped_column(String(500), nullable=True)  # email only
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    accountant = relationship("Accountant", back_populates="message_templates")
