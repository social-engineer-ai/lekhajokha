"""Tests for reconciliation confidence scoring logic."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.reconciliation_service import _compute_confidence


def _make_invoice(**overrides):
    inv = MagicMock()
    inv.total_amount = overrides.get("total_amount", Decimal("10000.00"))
    inv.invoice_date = overrides.get("invoice_date", date(2024, 3, 15))
    inv.invoice_type = overrides.get("invoice_type", "sales")
    inv.invoice_number = overrides.get("invoice_number", "INV-001")
    inv.seller_gstin = overrides.get("seller_gstin", "27AABCU9603R1ZM")
    inv.seller_name = overrides.get("seller_name", "Acme Industries")
    inv.buyer_gstin = overrides.get("buyer_gstin", "07AAACR5055K1Z5")
    inv.buyer_name = overrides.get("buyer_name", "Beta Corp")
    return inv


def _make_transaction(**overrides):
    txn = MagicMock()
    txn.amount = overrides.get("amount", Decimal("10000.00"))
    txn.transaction_date = overrides.get("transaction_date", date(2024, 3, 15))
    txn.transaction_type = overrides.get("transaction_type", "credit")
    txn.raw_description = overrides.get("raw_description", "NEFT/ICIC0001234/BETA CORP/REF123")
    txn.parsed_counterparty = overrides.get("parsed_counterparty", "BETA CORP")
    return txn


def _make_client(**overrides):
    cl = MagicMock()
    cl.gstin = overrides.get("gstin", "27AABCU9603R1ZM")
    return cl


class TestAmountScoring:
    """Amount match = 45 pts max."""

    def test_exact_amount_45pts(self):
        inv = _make_invoice(total_amount=Decimal("10000.00"))
        txn = _make_transaction(amount=Decimal("10000.00"))
        score = _compute_confidence(inv, txn, _make_client())
        # Should include 45 for amount + other components
        assert score >= 45

    def test_within_1_rupee_still_45(self):
        inv = _make_invoice(total_amount=Decimal("10000.00"))
        txn = _make_transaction(amount=Decimal("10000.50"))
        score = _compute_confidence(inv, txn, _make_client())
        assert score >= 45

    def test_within_2pct_gets_30(self):
        inv = _make_invoice(total_amount=Decimal("10000.00"))
        txn = _make_transaction(amount=Decimal("10150.00"))  # 1.5% diff
        score = _compute_confidence(inv, txn, _make_client())
        # Amount should contribute 30, not 45
        assert score >= 30

    def test_within_5pct_gets_15(self):
        inv = _make_invoice(total_amount=Decimal("10000.00"))
        txn = _make_transaction(amount=Decimal("10400.00"))  # 4% diff
        score = _compute_confidence(inv, txn, _make_client())
        assert score >= 15

    def test_over_5pct_gets_0(self):
        inv = _make_invoice(total_amount=Decimal("10000.00"))
        txn = _make_transaction(amount=Decimal("16000.00"))  # 60% diff
        # Zero out all other scoring factors
        txn.raw_description = "NOTHING"
        txn.parsed_counterparty = "NOBODY"
        inv.buyer_gstin = None
        inv.buyer_name = None
        inv.invoice_number = None
        inv.invoice_date = None
        txn.transaction_date = None
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 0


class TestDateScoring:
    """Date proximity = 25 pts max."""

    def test_same_day_25pts(self):
        inv = _make_invoice(
            invoice_date=date(2024, 3, 15),
            total_amount=None,  # zero out amount
            invoice_number=None, buyer_gstin=None, buyer_name=None,
        )
        txn = _make_transaction(
            transaction_date=date(2024, 3, 15),
            amount=Decimal("0"),
            raw_description="X", parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 25

    def test_within_3_days_20pts(self):
        inv = _make_invoice(
            invoice_date=date(2024, 3, 15),
            total_amount=None, invoice_number=None, buyer_gstin=None, buyer_name=None,
        )
        txn = _make_transaction(
            transaction_date=date(2024, 3, 17),
            amount=Decimal("0"),
            raw_description="X", parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 20

    def test_within_7_days_15pts(self):
        inv = _make_invoice(
            invoice_date=date(2024, 3, 15),
            total_amount=None, invoice_number=None, buyer_gstin=None, buyer_name=None,
        )
        txn = _make_transaction(
            transaction_date=date(2024, 3, 20),
            amount=Decimal("0"),
            raw_description="X", parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 15

    def test_within_14_days_10pts(self):
        inv = _make_invoice(
            invoice_date=date(2024, 3, 1),
            total_amount=None, invoice_number=None, buyer_gstin=None, buyer_name=None,
        )
        txn = _make_transaction(
            transaction_date=date(2024, 3, 12),
            amount=Decimal("0"),
            raw_description="X", parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 10


class TestGSTINCounterpartyScoring:
    """GSTIN/counterparty match = 15 pts max."""

    def test_buyer_gstin_in_description_15pts(self):
        inv = _make_invoice(
            total_amount=None, invoice_date=None, invoice_number=None,
            buyer_gstin="07AAACR5055K1Z5",
        )
        txn = _make_transaction(
            amount=Decimal("0"),
            transaction_date=None,
            raw_description="NEFT/07AAACR5055K1Z5/PAYMENT",
            parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 15

    def test_buyer_name_in_counterparty_15pts(self):
        inv = _make_invoice(
            total_amount=None, invoice_date=None, invoice_number=None,
            buyer_gstin=None, buyer_name="BETA CORP",
        )
        txn = _make_transaction(
            amount=Decimal("0"),
            transaction_date=None,
            raw_description="X",
            parsed_counterparty="BETA CORP",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 15

    def test_partial_name_match_8pts(self):
        inv = _make_invoice(
            total_amount=None, invoice_date=None, invoice_number=None,
            buyer_gstin=None, buyer_name="BETA CORPORATION LIMITED",
        )
        txn = _make_transaction(
            amount=Decimal("0"),
            transaction_date=None,
            raw_description="X",
            parsed_counterparty="BETA INDUSTRIES",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 8


class TestReferenceScoring:
    """Reference/invoice number match = 15 pts max."""

    def test_invoice_number_in_description_15pts(self):
        inv = _make_invoice(
            total_amount=None, invoice_date=None,
            buyer_gstin=None, buyer_name=None,
            invoice_number="INV-2024-042",
        )
        txn = _make_transaction(
            amount=Decimal("0"),
            transaction_date=None,
            raw_description="NEFT/PAYMENT FOR INV-2024-042",
            parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 15

    def test_stripped_prefix_match_8pts(self):
        inv = _make_invoice(
            total_amount=None, invoice_date=None,
            buyer_gstin=None, buyer_name=None,
            invoice_number="INV-20240042",
        )
        txn = _make_transaction(
            amount=Decimal("0"),
            transaction_date=None,
            raw_description="PAYMENT 20240042 RECEIVED",
            parsed_counterparty="X",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 8


class TestCombinedScoring:
    def test_perfect_match_reaches_100(self):
        inv = _make_invoice(
            invoice_number="INV-001",
            buyer_gstin="07AAACR5055K1Z5",
        )
        txn = _make_transaction(
            raw_description="NEFT/07AAACR5055K1Z5/INV-001/PAYMENT",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 100  # 45 + 25 + 15 + 15

    def test_above_auto_confirm_threshold(self):
        inv = _make_invoice()
        txn = _make_transaction()
        score = _compute_confidence(inv, txn, _make_client())
        assert score >= 80  # Should auto-confirm

    def test_purchase_uses_seller_info(self):
        inv = _make_invoice(
            invoice_type="purchase",
            total_amount=None, invoice_date=None, invoice_number=None,
            seller_gstin=None, seller_name="VENDOR XYZ",
        )
        txn = _make_transaction(
            transaction_type="debit",
            amount=Decimal("0"),
            transaction_date=None,
            raw_description="X",
            parsed_counterparty="VENDOR XYZ",
        )
        score = _compute_confidence(inv, txn, _make_client())
        assert score == 15
