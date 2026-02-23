"""Twilio webhook for inbound WhatsApp messages. No auth middleware."""

import uuid
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.database import async_session
from app.models.client import Client
from app.models.message import Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/twilio")
async def twilio_webhook(request: Request):
    """Receive inbound WhatsApp messages from Twilio.

    Twilio sends form-encoded data with From, Body, MessageSid, etc.
    We look up the client by phone number and create an inbound Message.
    """
    try:
        form = await request.form()
        from_number = str(form.get("From", ""))  # whatsapp:+919876543210
        body = str(form.get("Body", ""))
        message_sid = str(form.get("MessageSid", ""))
        profile_name = str(form.get("ProfileName", "")) or None

        # Strip whatsapp: prefix
        phone = from_number.replace("whatsapp:", "").strip()

        if not phone or not body:
            return {"status": "ignored", "reason": "missing From or Body"}

        async with async_session() as db:
            # Look up client by contact_phone
            # Try exact match first, then normalized variants
            result = await db.execute(
                select(Client).where(
                    Client.is_active == True,
                    Client.contact_phone.isnot(None),
                )
            )
            clients = list(result.scalars().all())

            matched_client = None
            normalized_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

            for c in clients:
                c_phone = (c.contact_phone or "").replace("+", "").replace(" ", "").replace("-", "")
                if c_phone and c_phone == normalized_phone:
                    matched_client = c
                    break
                # Also check with 91 prefix
                if c_phone and len(c_phone) == 10 and normalized_phone == f"91{c_phone}":
                    matched_client = c
                    break

            if not matched_client:
                logger.info(f"Inbound WhatsApp from unknown number {phone}, ignoring")
                return {"status": "ignored", "reason": "unknown sender"}

            msg = Message(
                id=uuid.uuid4(),
                client_id=matched_client.id,
                accountant_id=matched_client.accountant_id,
                channel="whatsapp",
                direction="inbound",
                content=body,
                status="delivered",
                message_type="text",
                external_id=message_sid,
                whatsapp_profile_name=profile_name,
                triggered_by="manual",
            )
            db.add(msg)
            await db.commit()

            logger.info(f"Inbound WhatsApp from {phone} → client {matched_client.id}")

        return {"status": "ok"}

    except Exception as e:
        logger.exception(f"Error processing Twilio webhook: {e}")
        return {"status": "error", "reason": str(e)[:200]}
