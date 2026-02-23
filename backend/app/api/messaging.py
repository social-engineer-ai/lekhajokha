import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.messaging_config import MessagingConfig
from app.models.message_template import MessageTemplate
from app.schemas.messaging import (
    MessagingConfigResponse,
    MessagingConfigUpdate,
    TestMessageRequest,
    TestMessageResponse,
    MessageTemplateResponse,
    MessageTemplateUpdate,
)
from app.services.whatsapp_service import send_whatsapp
from app.services.email_service import send_email

router = APIRouter(prefix="/messaging", tags=["messaging"])


@router.get("/config", response_model=MessagingConfigResponse)
async def get_messaging_config(
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messaging config (auto-create if missing)."""
    result = await db.execute(
        select(MessagingConfig).where(MessagingConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = MessagingConfig(
            id=uuid.uuid4(),
            accountant_id=current_user.id,
        )
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return config


@router.put("/config", response_model=MessagingConfigResponse)
async def update_messaging_config(
    data: MessagingConfigUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update WhatsApp/email settings."""
    result = await db.execute(
        select(MessagingConfig).where(MessagingConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = MessagingConfig(
            id=uuid.uuid4(),
            accountant_id=current_user.id,
        )
        db.add(config)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(config)
    return config


@router.post("/test-whatsapp", response_model=TestMessageResponse)
async def test_whatsapp(
    data: TestMessageRequest,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test WhatsApp message."""
    result = await db.execute(
        select(MessagingConfig).where(MessagingConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    twilio_config = None
    if config:
        twilio_config = {
            "twilio_account_sid": config.twilio_account_sid,
            "twilio_auth_token": config.twilio_auth_token,
            "twilio_whatsapp_number": config.twilio_whatsapp_number,
        }

    send_result = await send_whatsapp(
        to=data.to,
        body="Test message from LekhaJokha. If you received this, WhatsApp integration is working!",
        config=twilio_config,
    )

    if send_result["status"] == "failed":
        return TestMessageResponse(success=False, error=send_result.get("error", "Send failed"))
    return TestMessageResponse(success=True, message=f"Test message sent (SID: {send_result.get('sid')})")


@router.post("/test-email", response_model=TestMessageResponse)
async def test_email(
    data: TestMessageRequest,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a test email."""
    result = await db.execute(
        select(MessagingConfig).where(MessagingConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    smtp_config = None
    if config:
        smtp_config = {
            "smtp_host": config.smtp_host,
            "smtp_port": config.smtp_port,
            "smtp_username": config.smtp_username,
            "smtp_password": config.smtp_password,
            "smtp_from_email": config.smtp_from_email,
            "smtp_use_tls": config.smtp_use_tls,
        }

    send_result = await send_email(
        to=data.to,
        subject="LekhaJokha — Test Email",
        body="This is a test email from LekhaJokha. If you received this, email integration is working!",
        smtp_config=smtp_config,
    )

    if send_result["status"] == "failed":
        return TestMessageResponse(success=False, error=send_result.get("error", "Send failed"))
    return TestMessageResponse(success=True, message=f"Test email sent (ID: {send_result.get('message_id')})")


@router.get("/templates", response_model=list[MessageTemplateResponse])
async def list_templates(
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all templates (accountant-specific + system defaults)."""
    result = await db.execute(
        select(MessageTemplate).where(
            or_(
                MessageTemplate.accountant_id == current_user.id,
                MessageTemplate.accountant_id == None,
            )
        ).order_by(MessageTemplate.trigger_event, MessageTemplate.channel)
    )
    templates = list(result.scalars().all())

    # Deduplicate: accountant-specific overrides system default for same trigger+channel
    seen = set()
    deduplicated = []
    for t in templates:
        key = (t.trigger_event, t.channel)
        if t.accountant_id is not None:
            seen.add(key)
            deduplicated.append(t)
    for t in templates:
        key = (t.trigger_event, t.channel)
        if t.accountant_id is None and key not in seen:
            deduplicated.append(t)

    deduplicated.sort(key=lambda t: (t.trigger_event, t.channel))
    return deduplicated


@router.put("/templates/{template_id}", response_model=MessageTemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: MessageTemplateUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a template. Clone-on-write for system defaults."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # If system default (accountant_id=NULL), clone for this accountant
    if template.accountant_id is None:
        new_template = MessageTemplate(
            id=uuid.uuid4(),
            accountant_id=current_user.id,
            trigger_event=template.trigger_event,
            channel=template.channel,
            subject_template=data.subject_template if data.subject_template is not None else template.subject_template,
            body_template=data.body_template if data.body_template is not None else template.body_template,
            is_active=template.is_active,
        )
        db.add(new_template)
        await db.flush()
        await db.refresh(new_template)
        return new_template

    # Verify ownership
    if template.accountant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this template")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(template)
    return template


@router.post("/templates/{template_id}/toggle", response_model=MessageTemplateResponse)
async def toggle_template(
    template_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable/disable a template. Clone-on-write for system defaults."""
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # If system default, clone with toggled state
    if template.accountant_id is None:
        new_template = MessageTemplate(
            id=uuid.uuid4(),
            accountant_id=current_user.id,
            trigger_event=template.trigger_event,
            channel=template.channel,
            subject_template=template.subject_template,
            body_template=template.body_template,
            is_active=not template.is_active,
        )
        db.add(new_template)
        await db.flush()
        await db.refresh(new_template)
        return new_template

    if template.accountant_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this template")

    template.is_active = not template.is_active
    template.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(template)
    return template
