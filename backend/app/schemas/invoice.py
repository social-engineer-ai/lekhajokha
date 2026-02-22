import uuid
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel


class InvoiceLineItemResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    line_number: int
    description: str
    hsn_sac_code: str | None
    quantity: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    amount: Decimal
    gst_rate: Decimal | None
    cgst_amount: Decimal | None
    sgst_amount: Decimal | None
    igst_amount: Decimal | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    invoice_type: str
    file_name: str
    file_size_bytes: int
    invoice_number: str | None
    invoice_date: date | None
    seller_name: str | None
    seller_gstin: str | None
    buyer_name: str | None
    buyer_gstin: str | None
    place_of_supply: str | None
    taxable_amount: Decimal | None
    cgst_amount: Decimal | None
    sgst_amount: Decimal | None
    igst_amount: Decimal | None
    total_tax: Decimal | None
    total_amount: Decimal | None
    processing_status: str
    processing_error: str | None
    ocr_confidence: Decimal | None
    recon_status: str
    tally_sync_status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceDetailResponse(InvoiceResponse):
    line_items: list[InvoiceLineItemResponse] = []


class InvoiceUpdate(BaseModel):
    invoice_number: str | None = None
    invoice_date: date | None = None
    invoice_type: str | None = None
    seller_name: str | None = None
    seller_gstin: str | None = None
    buyer_name: str | None = None
    buyer_gstin: str | None = None
    place_of_supply: str | None = None
    taxable_amount: Decimal | None = None
    cgst_amount: Decimal | None = None
    sgst_amount: Decimal | None = None
    igst_amount: Decimal | None = None
    total_tax: Decimal | None = None
    total_amount: Decimal | None = None
