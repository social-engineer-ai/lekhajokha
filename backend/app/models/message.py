import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    accountant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accountants.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # whatsapp / email
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound / outbound
    content: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=True)  # email only
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending/sent/delivered/read/failed
    message_type: Mapped[str] = mapped_column(
        String(20), default="text"
    )  # text/notification/document
    attachment_path: Mapped[str] = mapped_column(String(500), nullable=True)  # MinIO path
    attachment_name: Mapped[str] = mapped_column(String(255), nullable=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=True)  # Twilio SID or email message-id
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    whatsapp_profile_name: Mapped[str] = mapped_column(String(255), nullable=True)
    triggered_by: Mapped[str] = mapped_column(
        String(50), default="manual"
    )  # manual/statement_processed/invoice_ocr_done/reconciliation_complete/gst_return_ready/tally_sync_done/payment_reminder
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    client = relationship("Client", back_populates="messages")
    accountant = relationship("Accountant", back_populates="messages")
