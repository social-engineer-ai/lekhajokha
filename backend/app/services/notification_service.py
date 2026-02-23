"""Automated notification dispatch after job completion."""

import re
import uuid
import logging

from sqlalchemy import select, or_

from app.database import async_session
from app.models.client import Client
from app.models.accountant import Accountant
from app.models.message import Message
from app.models.message_template import MessageTemplate
from app.models.messaging_config import MessagingConfig
from app.services.whatsapp_service import send_whatsapp
from app.services.email_service import send_email
from app.services.storage_service import get_presigned_url

logger = logging.getLogger(__name__)


async def notify(
    client_id: uuid.UUID,
    accountant_id: uuid.UUID,
    trigger_event: str,
    context_data: dict,
    attachment_path: str | None = None,
    attachment_name: str | None = None,
):
    """Send notifications for a trigger event. Fire-and-forget — never raises.

    Opens its own DB session (background task pattern).
    """
    try:
        async with async_session() as db:
            # 1. Load messaging config
            result = await db.execute(
                select(MessagingConfig).where(MessagingConfig.accountant_id == accountant_id)
            )
            config = result.scalar_one_or_none()
            if not config:
                logger.debug(f"No messaging config for accountant {accountant_id}, skipping notification")
                return

            # 2. Load client
            result = await db.execute(select(Client).where(Client.id == client_id))
            client = result.scalar_one_or_none()
            if not client:
                logger.warning(f"Client {client_id} not found for notification")
                return

            # 3. Load accountant for firm_name
            result = await db.execute(select(Accountant).where(Accountant.id == accountant_id))
            accountant = result.scalar_one_or_none()
            firm_name = accountant.firm_name or accountant.full_name if accountant else "LekhaJokha"
            context_data["firm_name"] = firm_name
            context_data.setdefault("client_name", client.contact_name or client.business_name)

            # 4. Load templates: accountant-specific first, then system defaults
            result = await db.execute(
                select(MessageTemplate).where(
                    MessageTemplate.trigger_event == trigger_event,
                    MessageTemplate.is_active == True,
                    or_(
                        MessageTemplate.accountant_id == accountant_id,
                        MessageTemplate.accountant_id == None,
                    ),
                )
            )
            templates = list(result.scalars().all())

            # Group by channel, prefer accountant-specific over system default
            channel_templates: dict[str, MessageTemplate] = {}
            for tmpl in templates:
                if tmpl.channel not in channel_templates or tmpl.accountant_id is not None:
                    channel_templates[tmpl.channel] = tmpl

            # 5. Dispatch per enabled channel
            # WhatsApp
            if (
                config.whatsapp_enabled
                and client.contact_phone
                and "whatsapp" in channel_templates
            ):
                tmpl = channel_templates["whatsapp"]
                body = render_template(tmpl.body_template, context_data)

                media_url = None
                if attachment_path:
                    try:
                        media_url = get_presigned_url(attachment_path)
                    except Exception:
                        logger.warning("Failed to generate presigned URL for WhatsApp media")

                msg = Message(
                    id=uuid.uuid4(),
                    client_id=client_id,
                    accountant_id=accountant_id,
                    channel="whatsapp",
                    direction="outbound",
                    content=body,
                    status="pending",
                    message_type="notification",
                    attachment_path=attachment_path,
                    attachment_name=attachment_name,
                    triggered_by=trigger_event,
                )
                db.add(msg)
                await db.flush()

                twilio_config = {
                    "twilio_account_sid": config.twilio_account_sid,
                    "twilio_auth_token": config.twilio_auth_token,
                    "twilio_whatsapp_number": config.twilio_whatsapp_number,
                }
                result = await send_whatsapp(
                    to=client.contact_phone,
                    body=body,
                    media_url=media_url,
                    config=twilio_config,
                )
                msg.external_id = result.get("sid")
                msg.status = "sent" if result["status"] != "failed" else "failed"
                msg.error_message = result.get("error")

            # Email
            if (
                config.email_enabled
                and client.contact_email
                and "email" in channel_templates
            ):
                tmpl = channel_templates["email"]
                body = render_template(tmpl.body_template, context_data)
                subject = render_template(tmpl.subject_template or trigger_event, context_data)

                # Prepare attachment bytes if path provided
                email_attachments = None
                if attachment_path and attachment_name:
                    try:
                        from app.services.storage_service import download_file
                        file_bytes = download_file(attachment_path)
                        email_attachments = [(attachment_name, file_bytes)]
                    except Exception:
                        logger.warning("Failed to download attachment for email")

                msg = Message(
                    id=uuid.uuid4(),
                    client_id=client_id,
                    accountant_id=accountant_id,
                    channel="email",
                    direction="outbound",
                    content=body,
                    subject=subject,
                    status="pending",
                    message_type="notification",
                    attachment_path=attachment_path,
                    attachment_name=attachment_name,
                    triggered_by=trigger_event,
                )
                db.add(msg)
                await db.flush()

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
                    body=body,
                    attachments=email_attachments,
                    smtp_config=smtp_config,
                )
                msg.external_id = result.get("message_id")
                msg.status = "sent" if result["status"] != "failed" else "failed"
                msg.error_message = result.get("error")

            await db.commit()
            logger.info(f"Notifications dispatched for {trigger_event} → client {client_id}")

    except Exception as e:
        logger.exception(f"Error sending notification for {trigger_event}: {e}")


def render_template(template: str, context: dict) -> str:
    """Simple {{key}} → value replacement."""
    def replacer(match):
        key = match.group(1).strip()
        return str(context.get(key, f"{{{{{key}}}}}"))

    return re.sub(r"\{\{(\w+)\}\}", replacer, template)
