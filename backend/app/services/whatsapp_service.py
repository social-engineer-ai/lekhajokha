"""WhatsApp messaging via Twilio (with mock mode for dev)."""

import logging
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


async def send_whatsapp(
    to: str,
    body: str,
    media_url: str | None = None,
    config: dict | None = None,
) -> dict:
    """Send a WhatsApp message via Twilio.

    Args:
        to: Phone number in E.164 format (e.g. +919876543210)
        body: Message body text
        media_url: Optional URL for media attachment (presigned MinIO URL)
        config: Dict with twilio_account_sid, twilio_auth_token, twilio_whatsapp_number

    Returns:
        {"sid": "...", "status": "queued"} on success
        {"sid": None, "status": "failed", "error": "..."} on failure
    """
    # Normalize phone to E.164
    phone = _normalize_phone(to)

    if settings.TWILIO_MOCK:
        fake_sid = f"SM{uuid.uuid4().hex[:32]}"
        logger.info(
            f"[MOCK WhatsApp] To: whatsapp:{phone} | Body: {body[:100]}... | "
            f"Media: {media_url or 'none'} | SID: {fake_sid}"
        )
        return {"sid": fake_sid, "status": "queued"}

    if not config:
        return {"sid": None, "status": "failed", "error": "Twilio not configured"}

    account_sid = config.get("twilio_account_sid")
    auth_token = config.get("twilio_auth_token")
    from_number = config.get("twilio_whatsapp_number")

    if not all([account_sid, auth_token, from_number]):
        return {"sid": None, "status": "failed", "error": "Twilio credentials incomplete"}

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)

        kwargs = {
            "from_": f"whatsapp:{from_number}",
            "to": f"whatsapp:{phone}",
            "body": body,
        }
        if media_url:
            kwargs["media_url"] = [media_url]

        message = client.messages.create(**kwargs)
        logger.info(f"WhatsApp sent to {phone}: SID={message.sid}")
        return {"sid": message.sid, "status": message.status}

    except Exception as e:
        logger.exception(f"WhatsApp send failed to {phone}: {e}")
        return {"sid": None, "status": "failed", "error": str(e)[:500]}


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format (+91XXXXXXXXXX)."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("91") and len(phone) == 12:
        return f"+{phone}"
    if len(phone) == 10:
        return f"+91{phone}"
    return f"+{phone}"
