import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.message import Message
from app.models.messaging_config import MessagingConfig
from app.schemas.messaging import MessageResponse, MessageSend, MessageResendResponse
from app.services.whatsapp_service import send_whatsapp
from app.services.email_service import send_email
from app.services.storage_service import get_presigned_url, download_file

router = APIRouter(prefix="/clients/{client_id}/messages", tags=["messages"])


async def _verify_client_ownership(
    client_id: uuid.UUID, current_user: Accountant, db: AsyncSession
) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.accountant_id == current_user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("", response_model=list[MessageResponse])
async def list_messages(
    client_id: uuid.UUID,
    channel: str | None = Query(None),
    direction: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List messages for a client (paginated, filterable)."""
    await _verify_client_ownership(client_id, current_user, db)

    query = select(Message).where(
        Message.client_id == client_id,
        Message.accountant_id == current_user.id,
    )
    if channel:
        query = query.where(Message.channel == channel)
    if direction:
        query = query.where(Message.direction == direction)

    query = query.order_by(desc(Message.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    client_id: uuid.UUID,
    data: MessageSend,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a manual message to a client."""
    client = await _verify_client_ownership(client_id, current_user, db)

    if data.channel not in ("whatsapp", "email"):
        raise HTTPException(status_code=400, detail="Channel must be 'whatsapp' or 'email'")

    # Check contact info
    if data.channel == "whatsapp" and not client.contact_phone:
        raise HTTPException(status_code=400, detail="Client has no phone number")
    if data.channel == "email" and not client.contact_email:
        raise HTTPException(status_code=400, detail="Client has no email address")

    # Load messaging config
    result = await db.execute(
        select(MessagingConfig).where(MessagingConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    # Create message record
    msg = Message(
        id=uuid.uuid4(),
        client_id=client_id,
        accountant_id=current_user.id,
        channel=data.channel,
        direction="outbound",
        content=data.content,
        subject=data.subject,
        status="pending",
        message_type="document" if data.attachment_path else "text",
        attachment_path=data.attachment_path,
        attachment_name=data.attachment_name,
        triggered_by="manual",
    )
    db.add(msg)
    await db.flush()

    # Dispatch
    if data.channel == "whatsapp":
        media_url = None
        if data.attachment_path:
            try:
                media_url = get_presigned_url(data.attachment_path)
            except Exception:
                pass

        twilio_config = None
        if config:
            twilio_config = {
                "twilio_account_sid": config.twilio_account_sid,
                "twilio_auth_token": config.twilio_auth_token,
                "twilio_whatsapp_number": config.twilio_whatsapp_number,
            }

        result = await send_whatsapp(
            to=client.contact_phone,
            body=data.content,
            media_url=media_url,
            config=twilio_config,
        )
        msg.external_id = result.get("sid")
        msg.status = "sent" if result["status"] != "failed" else "failed"
        msg.error_message = result.get("error")

    elif data.channel == "email":
        subject = data.subject or "Message from your accountant"

        email_attachments = None
        if data.attachment_path and data.attachment_name:
            try:
                file_bytes = download_file(data.attachment_path)
                email_attachments = [(data.attachment_name, file_bytes)]
            except Exception:
                pass

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

        result = await send_email(
            to=client.contact_email,
            subject=subject,
            body=data.content,
            attachments=email_attachments,
            smtp_config=smtp_config,
        )
        msg.external_id = result.get("message_id")
        msg.status = "sent" if result["status"] != "failed" else "failed"
        msg.error_message = result.get("error")

    await db.flush()
    await db.refresh(msg)
    return msg


@router.post("/{message_id}/resend", response_model=MessageResendResponse)
async def resend_message(
    client_id: uuid.UUID,
    message_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry sending a failed message."""
    client = await _verify_client_ownership(client_id, current_user, db)

    result = await db.execute(
        select(Message).where(
            Message.id == message_id,
            Message.client_id == client_id,
            Message.accountant_id == current_user.id,
        )
    )
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    if msg.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed messages can be resent")

    # Load messaging config
    result = await db.execute(
        select(MessagingConfig).where(MessagingConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()

    msg.status = "pending"
    msg.error_message = None

    if msg.channel == "whatsapp":
        media_url = None
        if msg.attachment_path:
            try:
                media_url = get_presigned_url(msg.attachment_path)
            except Exception:
                pass

        twilio_config = None
        if config:
            twilio_config = {
                "twilio_account_sid": config.twilio_account_sid,
                "twilio_auth_token": config.twilio_auth_token,
                "twilio_whatsapp_number": config.twilio_whatsapp_number,
            }

        send_result = await send_whatsapp(
            to=client.contact_phone,
            body=msg.content,
            media_url=media_url,
            config=twilio_config,
        )
        msg.external_id = send_result.get("sid")
        msg.status = "sent" if send_result["status"] != "failed" else "failed"
        msg.error_message = send_result.get("error")

    elif msg.channel == "email":
        email_attachments = None
        if msg.attachment_path and msg.attachment_name:
            try:
                file_bytes = download_file(msg.attachment_path)
                email_attachments = [(msg.attachment_name, file_bytes)]
            except Exception:
                pass

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
            to=client.contact_email,
            subject=msg.subject or "Message from your accountant",
            body=msg.content,
            attachments=email_attachments,
            smtp_config=smtp_config,
        )
        msg.external_id = send_result.get("message_id")
        msg.status = "sent" if send_result["status"] != "failed" else "failed"
        msg.error_message = send_result.get("error")

    msg.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return MessageResendResponse(id=msg.id, status=msg.status, external_id=msg.external_id)
