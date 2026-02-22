import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, BigInteger, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BankStatement(Base):
    __tablename__ = "bank_statements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_password_protected: Mapped[bool] = mapped_column(Boolean, default=False)
    period_from: Mapped[datetime] = mapped_column(Date, nullable=True)
    period_to: Mapped[datetime] = mapped_column(Date, nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, processing, completed, failed
    processing_error: Mapped[str] = mapped_column(Text, nullable=True)
    transactions_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    bank_account = relationship("BankAccount", back_populates="bank_statements")
    client = relationship("Client", back_populates="bank_statements")
    transactions = relationship("Transaction", back_populates="bank_statement", lazy="selectin")
