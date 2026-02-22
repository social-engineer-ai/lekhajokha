import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    accountant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accountants.id"), nullable=False, index=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[str] = mapped_column(String(15), nullable=True, index=True)
    pan: Mapped[str] = mapped_column(String(10), nullable=True, index=True)
    state_code: Mapped[str] = mapped_column(String(2), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(15), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    ingest_email: Mapped[str] = mapped_column(String(255), unique=True, nullable=True)
    gst_username: Mapped[str] = mapped_column(String(100), nullable=True)
    gst_filing_frequency: Mapped[str] = mapped_column(String(20), default="monthly")  # monthly/quarterly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    accountant = relationship("Accountant", back_populates="clients")
    bank_accounts = relationship("BankAccount", back_populates="client", lazy="selectin")
    jobs = relationship("Job", back_populates="client", lazy="selectin")
    bank_statements = relationship("BankStatement", back_populates="client", lazy="noload")
    transactions = relationship("Transaction", back_populates="client", lazy="noload")
    invoices = relationship("Invoice", back_populates="client", lazy="noload")
