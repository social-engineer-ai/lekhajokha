"""Integration tests for jobs API endpoint."""

import uuid

import pytest
from httpx import AsyncClient


class TestJobsAPI:
    async def test_get_job_after_recon_trigger(
        self, client: AsyncClient, auth_headers: dict, test_client_entity: dict
    ):
        cid = test_client_entity["id"]
        # Trigger a reconciliation job
        trigger_resp = await client.post(f"/api/v1/clients/{cid}/reconciliation/run", headers=auth_headers)
        assert trigger_resp.status_code == 202
        job_id = trigger_resp.json()["id"]

        # Fetch job by ID
        resp = await client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == job_id
        assert resp.json()["job_type"] == "reconciliation"

    async def test_get_nonexistent_job_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
