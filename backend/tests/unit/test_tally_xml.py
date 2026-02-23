"""Tests for Tally XML generation — sales, purchase, payment, receipt vouchers, batch XML, ledger."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from xml.etree.ElementTree import fromstring

from app.services.tally_xml import (
    generate_sales_voucher,
    generate_purchase_voucher,
    generate_payment_voucher,
    generate_receipt_voucher,
    generate_batch_xml,
    generate_ledger_xml,
)


def _make_invoice(**overrides):
    inv = MagicMock()
    inv.invoice_number = overrides.get("invoice_number", "INV-001")
    inv.invoice_date = overrides.get("invoice_date", date(2024, 3, 15))
    inv.invoice_type = overrides.get("invoice_type", "sales")
    inv.seller_name = overrides.get("seller_name", "Acme Industries")
    inv.seller_gstin = overrides.get("seller_gstin", "27AABCU9603R1ZM")
    inv.buyer_name = overrides.get("buyer_name", "Beta Corp")
    inv.buyer_gstin = overrides.get("buyer_gstin", "07AAACR5055K1Z5")
    inv.place_of_supply = overrides.get("place_of_supply", "Maharashtra (27)")
    inv.taxable_amount = overrides.get("taxable_amount", Decimal("50000.00"))
    inv.total_amount = overrides.get("total_amount", Decimal("59000.00"))
    inv.cgst_amount = overrides.get("cgst_amount", Decimal("4500.00"))
    inv.sgst_amount = overrides.get("sgst_amount", Decimal("4500.00"))
    inv.igst_amount = overrides.get("igst_amount", None)
    inv.line_items = overrides.get("line_items", [])
    return inv


def _make_client(**overrides):
    cl = MagicMock()
    cl.business_name = overrides.get("business_name", "Acme Industries Pvt Ltd")
    cl.gstin = overrides.get("gstin", "27AABCU9603R1ZM")
    cl.address = overrides.get("address", "Mumbai, Maharashtra")
    cl.state_code = overrides.get("state_code", "27")
    return cl


def _make_transaction(**overrides):
    txn = MagicMock()
    txn.transaction_date = overrides.get("transaction_date", date(2024, 3, 18))
    txn.raw_description = overrides.get("raw_description", "NEFT/PAYMENT FOR INV-001")
    return txn


def _make_match(**overrides):
    m = MagicMock()
    m.matched_amount = overrides.get("matched_amount", Decimal("59000.00"))
    return m


class TestSalesVoucher:
    def test_generates_valid_xml(self):
        xml_str = generate_sales_voucher(_make_invoice(), _make_client())
        root = fromstring(xml_str)
        assert root.tag == "ENVELOPE"

    def test_voucher_type_is_sales(self):
        xml_str = generate_sales_voucher(_make_invoice(), _make_client())
        root = fromstring(xml_str)
        voucher = root.find(".//VOUCHER")
        assert voucher.get("VCHTYPE") == "Sales"
        assert voucher.findtext("VOUCHERTYPENAME") == "Sales"

    def test_party_is_buyer(self):
        xml_str = generate_sales_voucher(_make_invoice(buyer_name="Test Buyer"), _make_client())
        root = fromstring(xml_str)
        assert root.findtext(".//PARTYNAME") == "Test Buyer"

    def test_gst_allocations(self):
        xml_str = generate_sales_voucher(_make_invoice(), _make_client())
        root = fromstring(xml_str)
        ledger_names = [e.findtext("LEDGERNAME") for e in root.findall(".//LEDGERENTRIES.LIST")]
        assert "CGST" in ledger_names
        assert "SGST" in ledger_names


class TestPurchaseVoucher:
    def test_voucher_type_is_purchase(self):
        xml_str = generate_purchase_voucher(_make_invoice(invoice_type="purchase"), _make_client())
        root = fromstring(xml_str)
        voucher = root.find(".//VOUCHER")
        assert voucher.get("VCHTYPE") == "Purchase"

    def test_party_is_seller(self):
        inv = _make_invoice(invoice_type="purchase", seller_name="Vendor Co")
        xml_str = generate_purchase_voucher(inv, _make_client())
        root = fromstring(xml_str)
        assert root.findtext(".//PARTYNAME") == "Vendor Co"


class TestPaymentVoucher:
    def test_payment_voucher_structure(self):
        xml_str = generate_payment_voucher(_make_match(), _make_invoice(), _make_transaction())
        root = fromstring(xml_str)
        voucher = root.find(".//VOUCHER")
        assert voucher.get("VCHTYPE") == "Payment"
        ledger_names = [e.findtext("LEDGERNAME") for e in root.findall(".//LEDGERENTRIES.LIST")]
        assert "Bank Account" in ledger_names


class TestReceiptVoucher:
    def test_receipt_voucher_structure(self):
        xml_str = generate_receipt_voucher(_make_match(), _make_invoice(), _make_transaction())
        root = fromstring(xml_str)
        voucher = root.find(".//VOUCHER")
        assert voucher.get("VCHTYPE") == "Receipt"


class TestBatchXML:
    def test_combines_multiple_vouchers(self):
        v1 = generate_sales_voucher(_make_invoice(invoice_number="S-001"), _make_client())
        v2 = generate_purchase_voucher(_make_invoice(invoice_number="P-001"), _make_client())
        batch = generate_batch_xml([v1, v2])
        root = fromstring(batch)
        tally_msgs = root.findall(".//TALLYMESSAGE")
        assert len(tally_msgs) == 2

    def test_empty_batch(self):
        batch = generate_batch_xml([])
        root = fromstring(batch)
        assert root.tag == "ENVELOPE"


class TestLedgerXML:
    def test_ledger_creation(self):
        cl = _make_client()
        xml_str = generate_ledger_xml(cl)
        root = fromstring(xml_str)
        ledger = root.find(".//LEDGER")
        assert ledger is not None
        assert ledger.get("NAME") == "Acme Industries Pvt Ltd"
        assert ledger.findtext("PARENT") == "Sundry Debtors"
        assert ledger.findtext("PARTYGSTIN") == "27AABCU9603R1ZM"
