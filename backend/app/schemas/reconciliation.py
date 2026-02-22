import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel


class InvoiceSummary(BaseModel):
    id: uuid.UUID
    invoice_number: str | None
    invoice_date: date | None
    invoice_type: str
    seller_name: str | None
    buyer_name: str | None
    total_amount: Decimal | None

    model_config = {"from_attributes": True}


class TransactionSummary(BaseModel):
    id: uuid.UUID
    transaction_date: date
    raw_description: str
    amount: float
    transaction_type: str
    parsed_counterparty: str | None
    transaction_mode: str | None

    model_config = {"from_attributes": True}


class ReconciliationMatchResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_id: uuid.UUID
    transaction_id: uuid.UUID
    confidence_score: Decimal
    matched_amount: Decimal
    is_confirmed: bool
    match_method: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    invoice_summary: InvoiceSummary | None = None
    transaction_summary: TransactionSummary | None = None

    model_config = {"from_attributes": True}


class ReconciliationMatchCreate(BaseModel):
    invoice_id: uuid.UUID
    transaction_id: uuid.UUID
    matched_amount: Decimal | None = None  # defaults to invoice total_amount
    notes: str | None = None


class ReconciliationMatchUpdate(BaseModel):
    is_confirmed: bool | None = None
    matched_amount: Decimal | None = None
    notes: str | None = None


class ReconciliationSummary(BaseModel):
    total_invoices: int
    matched_invoices: int
    unmatched_invoices: int
    total_transactions: int
    matched_transactions: int
    unmatched_transactions: int
    total_invoice_amount: Decimal
    matched_invoice_amount: Decimal
    unmatched_invoice_amount: Decimal
