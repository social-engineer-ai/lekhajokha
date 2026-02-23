"""Integration tests for VPA API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


class TestVpaCRUD:
    async def test_create_vpa_entry(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.post(
            f"/api/v1/clients/{cid}/vpa",
            json={"vpa": "merchant@upi", "resolved_name": "Test Merchant"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["vpa"] == "merchant@upi"
        assert data["source"] == "manual"

    async def test_list_vpa_entries(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        await client.post(f"/api/v1/clients/{cid}/vpa", json={"vpa": "a@upi"}, headers=auth_headers)
        resp = await client.get(f"/api/v1/clients/{cid}/vpa", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_vpa_entry(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        create_resp = await client.post(f"/api/v1/clients/{cid}/vpa", json={"vpa": "b@ybl"}, headers=auth_headers)
        vpa_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/v1/clients/{cid}/vpa/{vpa_id}",
            json={"resolved_name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["resolved_name"] == "Updated Name"

    async def test_delete_vpa_entry(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        create_resp = await client.post(f"/api/v1/clients/{cid}/vpa", json={"vpa": "c@paytm"}, headers=auth_headers)
        vpa_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/clients/{cid}/vpa/{vpa_id}", headers=auth_headers)
        assert resp.status_code == 204


class TestVpaSummary:
    async def test_summary_empty(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/vpa/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_vpa_entries"] == 0


class TestVpaActions:
    async def test_resolve_creates_job(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.post(f"/api/v1/clients/{cid}/vpa/resolve", headers=auth_headers)
        assert resp.status_code == 202
        assert resp.json()["job_type"] == "vpa_resolution"

    async def test_verify_vpa_cashfree(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        create_resp = await client.post(f"/api/v1/clients/{cid}/vpa", json={"vpa": "merchant@upi"}, headers=auth_headers)
        vpa_id = create_resp.json()["id"]
        resp = await client.post(f"/api/v1/clients/{cid}/vpa/{vpa_id}/verify", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["source"] == "cashfree_mock"

    async def test_collect_no_unresolved(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.post(f"/api/v1/clients/{cid}/vpa/collect", headers=auth_headers)
        assert resp.status_code == 200
        assert "No unresolved" in resp.json()["message"]
