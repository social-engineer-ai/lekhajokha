"""Integration tests for messaging config and templates API."""

import pytest
from httpx import AsyncClient


class TestMessagingConfig:
    async def test_get_config_auto_creates(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/messaging/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    async def test_update_config(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/v1/messaging/config",
            json={"twilio_account_sid": "ACtest123", "twilio_auth_token": "token123"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestTestMessages:
    async def test_test_whatsapp(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/messaging/test-whatsapp",
            json={"to": "+919876543210"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # Mock mode always succeeds
        assert resp.json()["success"] is True

    async def test_test_email(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/messaging/test-email",
            json={"to": "test@example.com"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestTemplates:
    async def test_list_templates(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/messaging/templates", headers=auth_headers)
        assert resp.status_code == 200
        # System seed templates should be returned
        assert isinstance(resp.json(), list)

    async def test_update_template_404(self, client: AsyncClient, auth_headers: dict):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.put(
            f"/api/v1/messaging/templates/{fake_id}",
            json={"body_template": "Updated body"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_toggle_template_404(self, client: AsyncClient, auth_headers: dict):
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/messaging/templates/{fake_id}/toggle",
            headers=auth_headers,
        )
        assert resp.status_code == 404
