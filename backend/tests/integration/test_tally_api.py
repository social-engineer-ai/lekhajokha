"""Integration tests for Tally config and sync API endpoints."""

import pytest
from httpx import AsyncClient


class TestTallyConfig:
    async def test_get_config_auto_creates(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/tally/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tally_host" in data

    async def test_update_config(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/v1/tally/config",
            json={"tally_host": "192.168.1.100", "tally_port": 9000, "company_name": "Test Co"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["tally_host"] == "192.168.1.100"

    async def test_test_connection(self, client: AsyncClient, auth_headers: dict):
        # First save config
        await client.put(
            "/api/v1/tally/config",
            json={"tally_host": "localhost", "tally_port": 9000},
            headers=auth_headers,
        )
        resp = await client.post("/api/v1/tally/test-connection", headers=auth_headers)
        assert resp.status_code == 200
        # Connection will fail in test env but endpoint should work
        assert "connected" in resp.json()
