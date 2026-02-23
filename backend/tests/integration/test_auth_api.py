"""Integration tests for auth endpoints: register, login, OTP, refresh, /me."""

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json=TEST_USER)
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json=TEST_USER)
        resp = await client.post("/api/v1/auth/register", json=TEST_USER)
        assert resp.status_code == 400
        assert "Email already registered" in resp.json()["detail"]

    async def test_register_duplicate_phone(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json=TEST_USER)
        user2 = {**TEST_USER, "email": "other@example.com"}
        resp = await client.post("/api/v1/auth/register", json=user2)
        assert resp.status_code == 400
        assert "Phone already registered" in resp.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        user = {**TEST_USER, "email": "not-an-email"}
        resp = await client.post("/api/v1/auth/register", json=user)
        assert resp.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        user = {**TEST_USER, "email": "new@example.com", "password": "123"}
        resp = await client.post("/api/v1/auth/register", json=user)
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json=TEST_USER)
        resp = await client.post("/api/v1/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post("/api/v1/auth/register", json=TEST_USER)
        resp = await client.post("/api/v1/auth/login", json={
            "email": TEST_USER["email"],
            "password": "WrongPassword1",
        })
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "Whatever123",
        })
        assert resp.status_code == 401


class TestOTP:
    async def test_send_otp(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/otp/send", json={"phone": "+919876543210"})
        assert resp.status_code == 200

    async def test_verify_otp_success(self, client: AsyncClient):
        phone = "+919876543210"
        await client.post("/api/v1/auth/otp/send", json={"phone": phone})
        resp = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "123456"})
        assert resp.status_code == 200
        assert resp.json()["verified"] is True

    async def test_verify_otp_wrong_code(self, client: AsyncClient):
        phone = "+919876543210"
        await client.post("/api/v1/auth/otp/send", json={"phone": phone})
        resp = await client.post("/api/v1/auth/otp/verify", json={"phone": phone, "otp": "000000"})
        assert resp.status_code == 400


class TestRefreshAndMe:
    async def test_refresh_token(self, client: AsyncClient, registered_user: dict):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": registered_user["refresh_token"],
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_with_invalid_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "garbage",
        })
        assert resp.status_code == 401

    async def test_get_me(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == TEST_USER["email"]
        assert data["full_name"] == TEST_USER["full_name"]

    async def test_update_me(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put("/api/v1/auth/me", json={"full_name": "Updated Name"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    async def test_me_without_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 403
