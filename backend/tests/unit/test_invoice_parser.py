"""Tests for invoice text parser — GSTIN, amounts, dates, line items, invoice type detection."""

from datetime import date
from decimal import Decimal

from app.services.invoice_parser import (
    parse_invoice_text,
    detect_invoice_type,
    _extract_gstins,
    _extract_invoice_number,
    _extract_invoice_date,
    _extract_amounts,
    _extract_line_items,
)


class TestGSTINExtraction:
    def test_extract_two_gstins(self):
        text = "Seller GSTIN: 27AABCU9603R1ZM\nBuyer GSTIN: 07AAACR5055K1Z5"
        gstins = _extract_gstins(text)
        assert len(gstins) == 2
        assert gstins[0] == "27AABCU9603R1ZM"
        assert gstins[1] == "07AAACR5055K1Z5"

    def test_deduplication(self):
        text = "GSTIN 27AABCU9603R1ZM appears twice 27AABCU9603R1ZM"
        gstins = _extract_gstins(text)
        assert len(gstins) == 1

    def test_no_gstin(self):
        assert _extract_gstins("No GSTIN here") == []


class TestInvoiceNumber:
    def test_invoice_no_colon(self):
        assert _extract_invoice_number("Invoice No: INV-2024-001") == "INV-2024-001"

    def test_inv_hash(self):
        assert _extract_invoice_number("Inv# GST/23/456") == "GST/23/456"

    def test_bill_no(self):
        assert _extract_invoice_number("Bill No. B-789") == "B-789"

    def test_no_match(self):
        assert _extract_invoice_number("Random text without invoice") is None


class TestInvoiceDate:
    def test_dd_mm_yyyy(self):
        text = "Invoice Date: 15/03/2024"
        assert _extract_invoice_date(text) == date(2024, 3, 15)

    def test_dd_mon_yyyy(self):
        text = "Date: 25-Jan-2024"
        assert _extract_invoice_date(text) == date(2024, 1, 25)

    def test_no_date(self):
        assert _extract_invoice_date("No date info") is None


class TestAmountExtraction:
    def test_all_amounts(self):
        text = """
        Taxable Amount: 1,00,000.00
        CGST @9%: 9,000.00
        SGST @9%: 9,000.00
        Total Tax: 18,000.00
        Grand Total: 1,18,000.00
        """
        amounts = _extract_amounts(text)
        assert amounts["taxable"] == Decimal("100000.00")
        assert amounts["cgst"] == Decimal("9000.00")
        assert amounts["sgst"] == Decimal("9000.00")
        assert amounts["total"] == Decimal("118000.00")

    def test_igst(self):
        text = "IGST @18%: 18,000.00"
        amounts = _extract_amounts(text)
        assert amounts["igst"] == Decimal("18000.00")


class TestLineItems:
    def test_basic_line_item(self):
        text = "1 | Steel Bars 7208 10 Nos 500.00 5,000.00"
        items = _extract_line_items(text)
        assert len(items) >= 1
        assert items[0].line_number == 1
        assert items[0].amount == Decimal("5000.00")

    def test_no_items(self):
        assert _extract_line_items("No table data here") == []


class TestInvoiceTypeDetection:
    def test_sales_when_seller_matches(self):
        assert detect_invoice_type("27AABCU9603R1ZM", "27AABCU9603R1ZM") == "sales"

    def test_purchase_when_different(self):
        assert detect_invoice_type("27AABCU9603R1ZM", "07AAACR5055K1Z5") == "purchase"

    def test_case_insensitive(self):
        assert detect_invoice_type("27aabcu9603r1zm", "27AABCU9603R1ZM") == "sales"

    def test_default_purchase_when_missing(self):
        assert detect_invoice_type(None, "27AABCU9603R1ZM") == "purchase"
        assert detect_invoice_type(None, None) == "purchase"


class TestFullParse:
    def test_full_invoice_text(self):
        text = """
        TAX INVOICE
        Acme Industries Pvt Ltd
        GSTIN: 27AABCU9603R1ZM

        Bill To:
        Beta Corp
        GSTIN: 07AAACR5055K1Z5

        Invoice No: INV-2024-042
        Invoice Date: 15/03/2024
        Place of Supply: Maharashtra (27)

        Taxable Amount: 50,000.00
        CGST @9%: 4,500.00
        SGST @9%: 4,500.00
        Total Tax: 9,000.00
        Grand Total: 59,000.00
        """
        result = parse_invoice_text(text)
        assert result.seller_gstin == "27AABCU9603R1ZM"
        assert result.buyer_gstin == "07AAACR5055K1Z5"
        assert result.invoice_number == "INV-2024-042"
        assert result.invoice_date == date(2024, 3, 15)
        assert result.taxable_amount == Decimal("50000.00")
        assert result.cgst_amount == Decimal("4500.00")
        assert result.total_amount == Decimal("59000.00")
