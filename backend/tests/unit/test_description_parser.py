"""Tests for bank transaction description parser — NEFT, UPI, IMPS, RTGS, ACH, CHEQUE, ATM."""

from app.services.parsers.description_parser import parse_description


class TestNEFT:
    def test_full_neft_with_ifsc(self):
        r = parse_description("NEFT/SBIN0001234/RAJESH KUMAR/123456789")
        assert r.mode == "NEFT"
        assert r.bank_ifsc == "SBIN0001234"
        assert r.counterparty == "RAJESH KUMAR"

    def test_neft_cr_prefix(self):
        r = parse_description("NEFT-CR-HDFC0002345-ACME CORP-REF999")
        assert r.mode == "NEFT"
        assert r.bank_ifsc == "HDFC0002345"

    def test_neft_simple_fallback(self):
        r = parse_description("NEFT-SOME PAYMENT INFO")
        assert r.mode == "NEFT"


class TestUPI:
    def test_upi_with_id(self):
        r = parse_description("UPI/412345678/AMIT SHARMA/amit@ybl")
        assert r.mode == "UPI"
        assert r.counterparty == "AMIT SHARMA"
        assert r.upi_id == "amit@ybl"
        assert r.reference == "412345678"

    def test_upi_without_id(self):
        r = parse_description("UPI/987654321/VENDOR SERVICES")
        assert r.mode == "UPI"
        assert r.counterparty == "VENDOR SERVICES"
        assert r.reference == "987654321"

    def test_upi_simple_fallback(self):
        r = parse_description("UPI PAYMENT merchant@paytm")
        assert r.mode == "UPI"
        assert r.upi_id == "merchant@paytm"


class TestIMPS:
    def test_imps_with_ifsc(self):
        r = parse_description("IMPS/567890123/PRIYA MEHTA/ICIC0003456")
        assert r.mode == "IMPS"
        assert r.counterparty == "PRIYA MEHTA"
        assert r.bank_ifsc == "ICIC0003456"
        assert r.reference == "567890123"

    def test_imps_simple(self):
        r = parse_description("IMPS-112233445-QUICK PAY")
        assert r.mode == "IMPS"


class TestRTGS:
    def test_rtgs_full(self):
        r = parse_description("RTGS/UTIB0004567/BIG CORP LTD/REF2024001")
        assert r.mode == "RTGS"
        assert r.bank_ifsc == "UTIB0004567"
        assert r.counterparty == "BIG CORP LTD"


class TestACH:
    def test_nach_pattern(self):
        r = parse_description("NACH/CR/INSURANCE PREMIUM/REF12345")
        assert r.mode == "ACH"
        assert r.counterparty == "INSURANCE PREMIUM"

    def test_ach_simple(self):
        r = parse_description("ACH-SBI LIFE PREMIUM")
        assert r.mode == "ACH"


class TestChequeATMInternal:
    def test_cheque_ref(self):
        r = parse_description("CHQ/000456")
        assert r.mode == "CHEQUE"
        assert r.reference == "000456"

    def test_atm_withdrawal(self):
        r = parse_description("ATM CASH WITHDRAWAL BRANCH XYZ")
        assert r.mode == "ATM"

    def test_internal_transfer(self):
        r = parse_description("TRF SAVINGS TO FD ACCOUNT")
        assert r.mode == "INTERNAL"

    def test_empty_returns_defaults(self):
        r = parse_description("")
        assert r.mode is None
        assert r.counterparty is None

    def test_unrecognised_returns_empty(self):
        r = parse_description("SOME RANDOM TEXT 12345")
        assert r.mode is None
