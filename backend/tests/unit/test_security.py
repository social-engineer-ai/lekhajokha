"""Tests for JWT token creation/validation and password hashing."""

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("MySecret123")
        assert verify_password("MySecret123", hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("MySecret123")
        assert not verify_password("WrongPass", hashed)

    def test_hash_is_not_plaintext(self):
        hashed = hash_password("plain")
        assert hashed != "plain"
        assert hashed.startswith("$2b$")


class TestJWT:
    def test_access_token_roundtrip(self):
        subject = "test-user-id"
        token = create_access_token(subject)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        subject = "test-user-id"
        token = create_refresh_token(subject)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

    def test_invalid_token_returns_none(self):
        assert decode_token("invalid.token.here") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("user-1")
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None
