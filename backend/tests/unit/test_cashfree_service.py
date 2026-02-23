"""Tests for Cashfree VPA verification service (mock mode)."""

import pytest

from app.services.cashfree_service import verify_vpa, _mock_verify


class TestMockVerify:
    def test_known_valid_vpa(self):
        result = _mock_verify("merchant@upi")
        assert result["is_valid"] is True
        assert result["registered_name"] == "Merchant Enterprises"
        assert result["source"] == "cashfree_mock"

    def test_known_invalid_vpa(self):
        result = _mock_verify("invalid@upi")
        assert result["is_valid"] is False
        assert result["registered_name"] is None

    def test_unknown_vpa_generates_name(self):
        result = _mock_verify("john.doe@okaxis")
        assert result["is_valid"] is True
        assert result["registered_name"] == "John Doe"
        assert result["source"] == "cashfree_mock"
