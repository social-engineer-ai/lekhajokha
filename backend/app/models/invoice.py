import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, BigInteger, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    invoice_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "sales" or "purchase"
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    seller_name: Mapped[str] = mapped_column(String(255), nullable=True)
    seller_gstin: Mapped[str] = mapped_column(String(15), nullable=True)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=True)
    buyer_gstin: Mapped[str] = mapped_column(String(15), nullable=True)
    place_of_supply: Mapped[str] = mapped_column(String(100), nullable=True)
    taxable_amount = mapped_column(Numeric(15, 2), nullable=True)
    cgst_amount = mapped_column(Numeric(15, 2), nullable=True)
    sgst_amount = mapped_column(Numeric(15, 2), nullable=True)
    igst_amount = mapped_column(Numeric(15, 2), nullable=True)
    total_tax = mapped_column(Numeric(15, 2), nullable=True)
    total_amount = mapped_column(Numeric(15, 2), nullable=True)
    raw_ocr_text: Mapped[str] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    processing_error: Mapped[str] = mapped_column(Text, nullable=True)
    ocr_confidence = mapped_column(Numeric(5, 2), nullable=True)  # 0-100 percentage
    recon_status: Mapped[str] = mapped_column(
        String(20), default="unmatched"
    )  # unmatched, matched, partial
    tally_sync_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, synced, error
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    client = relationship("Client", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", lazy="selectin")
    reconciliation_matches = relationship("ReconciliationMatch", back_populates="invoice", lazy="noload")
