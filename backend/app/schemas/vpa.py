import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class VpaEntryCreate(BaseModel):
    vpa: str
    resolved_name: Optional[str] = None
    gstin: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("vpa")
    @classmethod
    def validate_vpa(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("VPA must contain @")
        if len(v) < 3:
            raise ValueError("VPA is too short")
        return v

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$", v):
            raise ValueError("Invalid GSTIN format")
        return v


class VpaEntryUpdate(BaseModel):
    resolved_name: Optional[str] = None
    gstin: Optional[str] = None
    is_verified: Optional[bool] = None
    notes: Optional[str] = None

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if not re.match(r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$", v):
            raise ValueError("Invalid GSTIN format")
        return v


class VpaEntryResponse(BaseModel):
    id: UUID
    client_id: UUID
    vpa: str
    resolved_name: Optional[str]
    gstin: Optional[str]
    pan: Optional[str]
    source: str
    confidence: float
    is_verified: bool
    transaction_count: int
    last_seen_at: Optional[datetime]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VpaResolutionSummary(BaseModel):
    total_vpa_entries: int
    verified_count: int
    unverified_count: int
    total_upi_transactions: int
    tagged_transactions: int
    untagged_transactions: int
    sources_breakdown: dict[str, int]


class CashfreeVerifyResponse(BaseModel):
    vpa: str
    registered_name: Optional[str]
    is_valid: bool
    source: str
