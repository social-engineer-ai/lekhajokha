import re
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


GSTIN_PATTERN = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)


class ClientCreate(BaseModel):
    business_name: str
    gstin: str | None = None
    city: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    gst_username: str | None = None
    gst_filing_frequency: str = "monthly"

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.upper().strip()
        if not GSTIN_PATTERN.match(v):
            raise ValueError(
                "Invalid GSTIN format. Expected: 22AAAAA0000A1Z5"
            )
        return v


class ClientUpdate(BaseModel):
    business_name: str | None = None
    gstin: str | None = None
    city: str | None = None
    address: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    gst_username: str | None = None
    gst_filing_frequency: str | None = None
    tally_sync_scope: str | None = None

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.upper().strip()
        if not GSTIN_PATTERN.match(v):
            raise ValueError("Invalid GSTIN format")
        return v


class ClientResponse(BaseModel):
    id: uuid.UUID
    accountant_id: uuid.UUID
    business_name: str
    gstin: str | None
    pan: str | None
    state_code: str | None
    city: str | None
    address: str | None
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    ingest_email: str | None
    gst_username: str | None
    gst_filing_frequency: str
    tally_sync_scope: str
    is_active: bool
    created_at: datetime
    bank_accounts: list["BankAccountResponse"] = []

    model_config = {"from_attributes": True}


class BankAccountCreate(BaseModel):
    bank_name: str
    account_number: str
    ifsc_code: str | None = None
    branch_name: str | None = None
    account_type: str = "current"
    is_primary: bool = False

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.upper().strip()
        if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", v):
            raise ValueError("Invalid IFSC code format")
        return v


class BankAccountUpdate(BaseModel):
    bank_name: str | None = None
    account_number: str | None = None
    ifsc_code: str | None = None
    branch_name: str | None = None
    account_type: str | None = None
    is_primary: bool | None = None


class BankAccountResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    bank_name: str
    account_number: str
    ifsc_code: str | None
    branch_name: str | None
    account_type: str
    is_primary: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
