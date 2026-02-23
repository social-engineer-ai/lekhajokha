import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VpaEntry(Base):
    __tablename__ = "vpa_entries"
    __table_args__ = (
        UniqueConstraint("client_id", "vpa", name="uq_vpa_entry_client_vpa"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    vpa: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resolved_name: Mapped[str] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str] = mapped_column(String(15), nullable=True)
    pan: Mapped[str] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # transaction_aggregate, reconciliation, whatsapp_profile, manual, cashfree
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    client = relationship("Client", back_populates="vpa_entries")
    transactions = relationship("Transaction", back_populates="vpa_entry", lazy="noload")
