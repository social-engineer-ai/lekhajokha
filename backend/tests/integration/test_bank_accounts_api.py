"""Integration tests for bank account CRUD endpoints."""

import uuid
import pytest
from httpx import AsyncClient


SAMPLE_BANK_ACCOUNT = {
    "bank_name": "HDFC Bank",
    "account_number": "50100123456789",
    "ifsc_code": "HDFC0001234",
    "branch_name": "Andheri West",
    "account_type": "current",
    "is_primary": True,
}


class TestBankAccountCRUD:
    async def test_create_bank_account(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        resp = await client.post(f"/api/v1/clients/{cid}/bank-accounts/", json=SAMPLE_BANK_ACCOUNT, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["bank_name"] == "HDFC Bank"
        assert data["account_number"] == "50100123456789"

    async def test_list_bank_accounts(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        await client.post(f"/api/v1/clients/{cid}/bank-accounts/", json=SAMPLE_BANK_ACCOUNT, headers=auth_headers)
        resp = await client.get(f"/api/v1/clients/{cid}/bank-accounts/", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_get_bank_account(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        create_resp = await client.post(f"/api/v1/clients/{cid}/bank-accounts/", json=SAMPLE_BANK_ACCOUNT, headers=auth_headers)
        acc_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/clients/{cid}/bank-accounts/{acc_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == acc_id

    async def test_update_bank_account(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        create_resp = await client.post(f"/api/v1/clients/{cid}/bank-accounts/", json=SAMPLE_BANK_ACCOUNT, headers=auth_headers)
        acc_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/v1/clients/{cid}/bank-accounts/{acc_id}",
            json={"branch_name": "Bandra East"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["branch_name"] == "Bandra East"

    async def test_delete_bank_account(self, client: AsyncClient, auth_headers: dict, test_client_entity: dict):
        cid = test_client_entity["id"]
        create_resp = await client.post(f"/api/v1/clients/{cid}/bank-accounts/", json=SAMPLE_BANK_ACCOUNT, headers=auth_headers)
        acc_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/clients/{cid}/bank-accounts/{acc_id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_wrong_client_404(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(f"/api/v1/clients/{uuid.uuid4()}/bank-accounts/", headers=auth_headers)
        assert resp.status_code == 404
