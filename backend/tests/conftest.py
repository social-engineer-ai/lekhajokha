"""Core test fixtures: test DB, async client, auth helpers, mock storage."""

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Force test settings BEFORE importing app modules
os.environ.update({
    "DATABASE_URL": "postgresql+asyncpg://lekhajokha:lekhajokha_dev@postgres:5432/lekhajokha_test",
    "OTP_MOCK": "true",
    "OCR_ENGINE": "mock",
    "TWILIO_MOCK": "true",
    "SMTP_MOCK": "true",
    "CASHFREE_MOCK": "true",
    "DEBUG": "false",
})

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
import app.database as _app_db  # noqa: E402

TEST_DB_URL = os.environ["DATABASE_URL"]

# NullPool avoids asyncpg "another operation in progress" — each operation
# gets its own connection, no pool state to conflict.
_engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

_TRUNCATE_SQL = (
    "TRUNCATE TABLE reconciliation_matches, vpa_entries, transactions, "
    "bank_statements, bank_accounts, invoice_line_items, invoices, jobs, "
    "messages, message_templates, messaging_configs, tally_configs, "
    "clients, accountants CASCADE"
)


# ---- Shared event loop for entire test session ----

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---- Patch the app engine to use NullPool too ----

@pytest.fixture(scope="session", autouse=True)
def _patch_app_engine():
    """Replace the app's engine/session factory with NullPool versions."""
    _app_db.engine = _engine
    _app_db.async_session = _test_session_factory


# ---- Create tables once ----

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_tables():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _engine.dispose()


# ---- Per-test DB session ----

@pytest_asyncio.fixture()
async def db_session():
    """Fresh session per test, truncate all tables on teardown."""
    session = _test_session_factory()
    try:
        yield session
    finally:
        await session.close()
        async with _engine.begin() as conn:
            await conn.execute(text(_TRUNCATE_SQL))


# ---- httpx AsyncClient with DB override ----

@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncClient:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---- Auth helpers ----

TEST_USER = {
    "email": "test@example.com",
    "phone": "+919876543210",
    "password": "TestPass123",
    "full_name": "Test Accountant",
    "firm_name": "Test & Co",
}


@pytest_asyncio.fixture()
async def registered_user(client: AsyncClient) -> dict:
    resp = await client.post("/api/v1/auth/register", json=TEST_USER)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {**data, "user": TEST_USER}


@pytest_asyncio.fixture()
async def auth_headers(registered_user: dict) -> dict:
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


# ---- Client entity fixture ----

SAMPLE_CLIENT = {
    "business_name": "Acme Industries Pvt Ltd",
    "gstin": "27AABCU9603R1ZM",
    "city": "Mumbai",
    "contact_name": "Rajesh Sharma",
    "contact_phone": "+919876543211",
    "contact_email": "rajesh@acme.com",
}


@pytest_asyncio.fixture()
async def test_client_entity(client: AsyncClient, auth_headers: dict) -> dict:
    resp = await client.post("/api/v1/clients/", json=SAMPLE_CLIENT, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---- Mock storage (patch globally) ----

@pytest.fixture(autouse=True)
def mock_storage(monkeypatch):
    _files: dict[str, bytes] = {}

    def _upload(file_bytes: bytes, key: str) -> str:
        _files[key] = file_bytes
        return key

    def _download(key: str) -> bytes:
        return _files.get(key, b"mock file content")

    def _presigned(key: str, expires_in: int = 3600) -> str:
        return f"http://mock-minio/{key}"

    def _ensure():
        pass

    monkeypatch.setattr("app.services.storage_service.upload_file", _upload)
    monkeypatch.setattr("app.services.storage_service.download_file", _download)
    monkeypatch.setattr("app.services.storage_service.get_presigned_url", _presigned)
    monkeypatch.setattr("app.services.storage_service.ensure_bucket", _ensure)
