"""Integration tests for client CRUD endpoints."""

import pytest
import uuid
from httpx import AsyncClient

from tests.conftest import SAMPLE_CLIENT


class TestClientCRUD:
    async def test_create_client(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/clients/", json=SAMPLE_CLIENT, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["business_name"] == SAMPLE_CLIENT["business_name"]
        assert data["gstin"] == SAMPLE_CLIENT["gstin"]
        # PAN should be auto-extracted from GSTIN chars 3-12
        assert data["pan"] == "AABCU9603R"
        # State code from first 2 digits of GSTIN
        assert data["state_code"] == "27"
        # Ingest email should be generated
        assert data["ingest_email"] is not None
        assert "@ingest.lekhajokha.local" in data["ingest_email"]

    async def test_list_clients(self, client: AsyncClient, auth_headers: dict):
        await client.post("/api/v1/clients/", json=SAMPLE_CLIENT, headers=auth_headers)
        resp = await client.get("/api/v1/clients/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["business_name"] == SAMPLE_CLIENT["business_name"]

    async def test_get_client(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        client_id = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == client_id

    async def test_update_client(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        client_id = test_client_entity["id"]
        resp = await client.put(
            f"/api/v1/clients/{client_id}",
            json={"business_name": "Updated Corp"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["business_name"] == "Updated Corp"

    async def test_delete_client_soft(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        client_id = test_client_entity["id"]
        resp = await client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)
        assert resp.status_code == 204

        # Should not appear in list anymore
        resp = await client.get("/api/v1/clients/", headers=auth_headers)
        ids = [c["id"] for c in resp.json()]
        assert client_id not in ids

    async def test_create_client_without_gstin(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/clients/", json={"business_name": "No GSTIN Co"}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["gstin"] is None
        assert resp.json()["pan"] is None


class TestClientOwnershipIsolation:
    async def test_cannot_access_other_users_client(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        """Register a second user and verify they can't see the first user's client."""
        user2 = {
            "email": "user2@example.com",
            "phone": "+919876543299",
            "password": "Password123",
            "full_name": "Second User",
        }
        reg_resp = await client.post("/api/v1/auth/register", json=user2)
        token2 = reg_resp.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        client_id = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{client_id}", headers=headers2)
        assert resp.status_code == 404

    async def test_other_user_list_empty(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        user2 = {
            "email": "user2@example.com",
            "phone": "+919876543299",
            "password": "Password123",
            "full_name": "Second User",
        }
        reg_resp = await client.post("/api/v1/auth/register", json=user2)
        headers2 = {"Authorization": f"Bearer {reg_resp.json()['access_token']}"}

        resp = await client.get("/api/v1/clients/", headers=headers2)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_nonexistent_client_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(f"/api/v1/clients/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_no_auth_returns_403(self, client: AsyncClient):
        resp = await client.get("/api/v1/clients/")
        assert resp.status_code == 403
