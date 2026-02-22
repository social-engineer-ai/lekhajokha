import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.schemas.auth import (
    AccountantResponse,
    AccountantUpdateRequest,
    LoginRequest,
    OTPSendRequest,
    OTPVerifyRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import (
    authenticate,
    generate_tokens,
    get_accountant_by_email,
    get_accountant_by_phone,
    register_accountant,
    send_otp,
    verify_otp,
)
from app.utils.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_accountant_by_email(db, req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    existing_phone = await get_accountant_by_phone(db, req.phone)
    if existing_phone:
        raise HTTPException(status_code=400, detail="Phone already registered")
    accountant = await register_accountant(
        db, req.email, req.phone, req.password, req.full_name, req.firm_name
    )
    return generate_tokens(str(accountant.id))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    accountant = await authenticate(db, req.email, req.password)
    if not accountant:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return generate_tokens(str(accountant.id))


@router.post("/otp/send")
async def otp_send(req: OTPSendRequest):
    success = send_otp(req.phone)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP")
    return {"message": "OTP sent successfully"}


@router.post("/otp/verify")
async def otp_verify(req: OTPVerifyRequest):
    if not verify_otp(req.phone, req.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    return {"message": "OTP verified", "verified": True}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return generate_tokens(payload["sub"])


@router.get("/me", response_model=AccountantResponse)
async def get_me(current_user: Accountant = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=AccountantResponse)
async def update_me(
    req: AccountantUpdateRequest,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if req.full_name is not None:
        current_user.full_name = req.full_name
    if req.firm_name is not None:
        current_user.firm_name = req.firm_name
    await db.flush()
    await db.refresh(current_user)
    return current_user
