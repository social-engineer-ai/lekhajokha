import random
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.accountant import Accountant
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token

# In-memory OTP store (use Redis in production)
_otp_store: dict[str, str] = {}


async def register_accountant(
    db: AsyncSession,
    email: str,
    phone: str,
    password: str,
    full_name: str,
    firm_name: str | None = None,
) -> Accountant:
    accountant = Accountant(
        id=uuid.uuid4(),
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        full_name=full_name,
        firm_name=firm_name,
    )
    db.add(accountant)
    await db.flush()
    await db.refresh(accountant)
    return accountant


async def authenticate(db: AsyncSession, email: str, password: str) -> Accountant | None:
    result = await db.execute(select(Accountant).where(Accountant.email == email))
    accountant = result.scalar_one_or_none()
    if not accountant or not verify_password(password, accountant.hashed_password):
        return None
    return accountant


def generate_tokens(accountant_id: str) -> dict:
    return {
        "access_token": create_access_token(accountant_id),
        "refresh_token": create_refresh_token(accountant_id),
        "token_type": "bearer",
    }


def send_otp(phone: str) -> bool:
    if settings.OTP_MOCK:
        _otp_store[phone] = settings.OTP_FIXED_CODE
        return True
    # Real SMS integration would go here
    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = otp
    # TODO: send via MSG91/Twilio
    return True


def verify_otp(phone: str, otp: str) -> bool:
    stored = _otp_store.get(phone)
    if stored and stored == otp:
        _otp_store.pop(phone, None)
        return True
    return False


async def get_accountant_by_id(db: AsyncSession, accountant_id: uuid.UUID) -> Accountant | None:
    result = await db.execute(select(Accountant).where(Accountant.id == accountant_id))
    return result.scalar_one_or_none()


async def get_accountant_by_email(db: AsyncSession, email: str) -> Accountant | None:
    result = await db.execute(select(Accountant).where(Accountant.email == email))
    return result.scalar_one_or_none()


async def get_accountant_by_phone(db: AsyncSession, phone: str) -> Accountant | None:
    result = await db.execute(select(Accountant).where(Accountant.phone == phone))
    return result.scalar_one_or_none()
