"""Integration tests for messages API (list, send, resend)."""

import pytest
from httpx import AsyncClient


class TestMessagesAPI:
    async def test_list_messages_empty(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/messages", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_send_whatsapp_message(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.post(
            f"/api/v1/clients/{cid}/messages",
            json={"channel": "whatsapp", "content": "Hello from tests"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["channel"] == "whatsapp"
        assert data["direction"] == "outbound"

    async def test_send_email_message(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.post(
            f"/api/v1/clients/{cid}/messages",
            json={"channel": "email", "content": "Hello from tests", "subject": "Test Subject"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["channel"] == "email"
