import uuid
from datetime import datetime, date

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: uuid.UUID
    bank_statement_id: uuid.UUID
    bank_account_id: uuid.UUID
    client_id: uuid.UUID
    transaction_date: date
    value_date: date | None
    reference_number: str | None
    cheque_ref_no: str | None
    raw_description: str
    parsed_counterparty: str | None
    parsed_bank_ifsc: str | None
    parsed_upi_id: str | None
    transaction_mode: str | None
    amount: float
    transaction_type: str
    running_balance: float | None
    category: str | None
    sub_category: str | None
    recon_status: str
    tally_sync_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransactionUpdate(BaseModel):
    category: str | None = None
    sub_category: str | None = None
    recon_status: str | None = None


class BankStatementResponse(BaseModel):
    id: uuid.UUID
    bank_account_id: uuid.UUID
    client_id: uuid.UUID
    file_name: str
    file_size_bytes: int
    is_password_protected: bool
    period_from: date | None
    period_to: date | None
    processing_status: str
    processing_error: str | None
    transactions_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BankStatementDetailResponse(BankStatementResponse):
    transactions: list[TransactionResponse] = []
