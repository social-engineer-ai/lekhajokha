import uuid
from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    job_type: str
    status: str
    result_summary: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}
