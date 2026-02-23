"""Integration tests for webhook endpoints (Twilio inbound)."""

import pytest
from httpx import AsyncClient


class TestTwilioWebhook:
    async def test_twilio_inbound_whatsapp(self, client: AsyncClient):
        """POST form-encoded Twilio webhook data — should not require auth."""
        resp = await client.post(
            "/api/v1/webhooks/twilio",
            data={
                "From": "whatsapp:+919876543210",
                "To": "whatsapp:+14155238886",
                "Body": "Hello from client",
                "ProfileName": "Rajesh Sharma",
                "MessageSid": "SM1234567890",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        # Should accept even without matching accountant — returns ok or ignored
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "ignored")
