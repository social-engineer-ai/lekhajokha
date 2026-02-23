"""Email messaging via SMTP (with mock mode for dev)."""

import logging
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from app.config import settings

logger = logging.getLogger(__name__)


async def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]] | None = None,
    smtp_config: dict | None = None,
) -> dict:
    """Send an email via SMTP.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
        attachments: Optional list of (filename, file_bytes) tuples
        smtp_config: Dict with smtp_host, smtp_port, smtp_username, smtp_password,
                     smtp_from_email, smtp_use_tls

    Returns:
        {"message_id": "...", "status": "sent"} on success
        {"message_id": None, "status": "failed", "error": "..."} on failure
    """
    if settings.SMTP_MOCK:
        fake_id = f"<{uuid.uuid4().hex}@mock.lekhajokha.local>"
        att_names = [a[0] for a in attachments] if attachments else []
        logger.info(
            f"[MOCK Email] To: {to} | Subject: {subject} | "
            f"Body: {body[:100]}... | Attachments: {att_names} | ID: {fake_id}"
        )
        return {"message_id": fake_id, "status": "sent"}

    if not smtp_config:
        return {"message_id": None, "status": "failed", "error": "SMTP not configured"}

    host = smtp_config.get("smtp_host")
    port = smtp_config.get("smtp_port", 587)
    username = smtp_config.get("smtp_username")
    password = smtp_config.get("smtp_password")
    from_email = smtp_config.get("smtp_from_email")
    use_tls = smtp_config.get("smtp_use_tls", True)

    if not all([host, username, password, from_email]):
        return {"message_id": None, "status": "failed", "error": "SMTP credentials incomplete"}

    try:
        import aiosmtplib

        msg = MIMEMultipart()
        msg["From"] = from_email
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachments:
            for filename, file_bytes in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(file_bytes)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)

        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            start_tls=not use_tls,
        )

        message_id = msg.get("Message-ID", f"<{uuid.uuid4().hex}@{host}>")
        logger.info(f"Email sent to {to}: ID={message_id}")
        return {"message_id": message_id, "status": "sent"}

    except Exception as e:
        logger.exception(f"Email send failed to {to}: {e}")
        return {"message_id": None, "status": "failed", "error": str(e)[:500]}
