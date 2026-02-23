import uuid
from datetime import datetime

from pydantic import BaseModel


# --- Message ---

class MessageResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    accountant_id: uuid.UUID
    channel: str
    direction: str
    content: str
    subject: str | None
    status: str
    message_type: str
    attachment_path: str | None
    attachment_name: str | None
    external_id: str | None
    error_message: str | None
    triggered_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageSend(BaseModel):
    channel: str  # whatsapp / email
    content: str
    subject: str | None = None  # email only
    attachment_path: str | None = None
    attachment_name: str | None = None


class MessageResendResponse(BaseModel):
    id: uuid.UUID
    status: str
    external_id: str | None


# --- MessagingConfig ---

class MessagingConfigResponse(BaseModel):
    id: uuid.UUID
    accountant_id: uuid.UUID
    whatsapp_enabled: bool
    email_enabled: bool
    twilio_account_sid: str | None
    twilio_whatsapp_number: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_from_email: str | None
    smtp_use_tls: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessagingConfigUpdate(BaseModel):
    whatsapp_enabled: bool | None = None
    email_enabled: bool | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None  # write-only
    twilio_whatsapp_number: str | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None  # write-only
    smtp_from_email: str | None = None
    smtp_use_tls: bool | None = None


# --- Test ---

class TestMessageRequest(BaseModel):
    to: str


class TestMessageResponse(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None


# --- Templates ---

class MessageTemplateResponse(BaseModel):
    id: uuid.UUID
    accountant_id: uuid.UUID | None
    trigger_event: str
    channel: str
    subject_template: str | None
    body_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageTemplateUpdate(BaseModel):
    subject_template: str | None = None
    body_template: str | None = None
