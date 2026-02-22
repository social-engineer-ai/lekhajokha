import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_statements.id"), nullable=False, index=True
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True
    )
    transaction_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    value_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=True)
    cheque_ref_no: Mapped[str] = mapped_column(String(50), nullable=True)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_counterparty: Mapped[str] = mapped_column(String(255), nullable=True)
    parsed_bank_ifsc: Mapped[str] = mapped_column(String(11), nullable=True)
    parsed_upi_id: Mapped[str] = mapped_column(String(255), nullable=True)
    transaction_mode: Mapped[str] = mapped_column(
        String(20), nullable=True
    )  # NEFT, UPI, IMPS, RTGS, ACH, INTERNAL, CASH, CHEQUE, ATM
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)  # debit, credit
    running_balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=True)
    sub_category: Mapped[str] = mapped_column(String(100), nullable=True)
    recon_status: Mapped[str] = mapped_column(
        String(20), default="unmatched"
    )  # unmatched, matched, manual
    tally_sync_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, synced, error
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    bank_statement = relationship("BankStatement", back_populates="transactions")
    bank_account = relationship("BankAccount", back_populates="transactions")
    client = relationship("Client", back_populates="transactions")
    reconciliation_matches = relationship("ReconciliationMatch", back_populates="transaction", lazy="noload")
