import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, DateTime, ForeignKey, Text, String, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    hsn_sac_code: Mapped[str] = mapped_column(String(10), nullable=True)
    quantity = mapped_column(Numeric(12, 3), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=True)  # "Nos", "Kgs", "Ltrs", etc.
    unit_price = mapped_column(Numeric(15, 2), nullable=True)
    amount = mapped_column(Numeric(15, 2), nullable=False)
    gst_rate = mapped_column(Numeric(5, 2), nullable=True)  # 5, 12, 18, 28 etc.
    cgst_amount = mapped_column(Numeric(15, 2), nullable=True)
    sgst_amount = mapped_column(Numeric(15, 2), nullable=True)
    igst_amount = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    invoice = relationship("Invoice", back_populates="line_items")
