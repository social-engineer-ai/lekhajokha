import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TallyConfigResponse(BaseModel):
    id: uuid.UUID
    accountant_id: uuid.UUID
    tally_host: str
    tally_port: int
    company_name: str | None
    is_connected: bool
    last_sync_at: datetime | None

    model_config = {"from_attributes": True}


class TallyConfigUpdate(BaseModel):
    tally_host: str | None = None
    tally_port: int | None = None
    company_name: str | None = None


class TallyConnectionTest(BaseModel):
    connected: bool
    company_name: str | None = None
    error: str | None = None


class TallySyncRequest(BaseModel):
    scope: str | None = None  # override client default: invoices_only / invoices_and_reconciled / all


class TallyExportRequest(BaseModel):
    month: int  # 1-12
    year: int
    scope: str | None = None
