import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str
    password: str
    full_name: str
    firm_name: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned.startswith("+91"):
            cleaned = "+91" + cleaned.lstrip("+")
        digits = cleaned.replace("+", "")
        if len(digits) != 12:  # 91 + 10 digits
            raise ValueError("Phone must be a valid 10-digit Indian number")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPSendRequest(BaseModel):
    phone: str


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccountantResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: str
    full_name: str
    firm_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountantUpdateRequest(BaseModel):
    full_name: str | None = None
    firm_name: str | None = None


class ResetPasswordRequest(BaseModel):
    phone: str
    otp: str
    new_password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if not cleaned.startswith("+91"):
            cleaned = "+91" + cleaned.lstrip("+")
        digits = cleaned.replace("+", "")
        if len(digits) != 12:
            raise ValueError("Phone must be a valid 10-digit Indian number")
        return cleaned

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
