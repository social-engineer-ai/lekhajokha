"""Tally Prime XML generator for vouchers and ledgers."""

from datetime import date
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

from app.models.invoice import Invoice
from app.models.invoice_line_item import InvoiceLineItem
from app.models.client import Client
from app.models.transaction import Transaction
from app.models.reconciliation_match import ReconciliationMatch


def _fmt_date(d: date | None) -> str:
    """Format date as YYYYMMDD for Tally."""
    if d is None:
        return ""
    return d.strftime("%Y%m%d")


def _fmt_amount(val: Decimal | None) -> str:
    if val is None:
        return "0.00"
    return f"{val:.2f}"


def _add_text(parent: Element, tag: str, text: str) -> Element:
    elem = SubElement(parent, tag)
    elem.text = text
    return elem


def _build_gst_allocation(voucher: Element, invoice: Invoice) -> None:
    """Add GST allocation entries to a voucher."""
    if invoice.cgst_amount and invoice.cgst_amount > 0:
        ledger = SubElement(voucher, "LEDGERENTRIES.LIST")
        _add_text(ledger, "LEDGERNAME", "CGST")
        _add_text(ledger, "ISDEEMEDPOSITIVE", "No")
        _add_text(ledger, "AMOUNT", f"-{_fmt_amount(invoice.cgst_amount)}")

    if invoice.sgst_amount and invoice.sgst_amount > 0:
        ledger = SubElement(voucher, "LEDGERENTRIES.LIST")
        _add_text(ledger, "LEDGERNAME", "SGST")
        _add_text(ledger, "ISDEEMEDPOSITIVE", "No")
        _add_text(ledger, "AMOUNT", f"-{_fmt_amount(invoice.sgst_amount)}")

    if invoice.igst_amount and invoice.igst_amount > 0:
        ledger = SubElement(voucher, "LEDGERENTRIES.LIST")
        _add_text(ledger, "LEDGERNAME", "IGST")
        _add_text(ledger, "ISDEEMEDPOSITIVE", "No")
        _add_text(ledger, "AMOUNT", f"-{_fmt_amount(invoice.igst_amount)}")


def _build_inventory_entries(voucher: Element, line_items: list[InvoiceLineItem]) -> None:
    """Add inventory/item entries from invoice line items."""
    for item in line_items:
        inv_entry = SubElement(voucher, "ALLINVENTORYENTRIES.LIST")
        _add_text(inv_entry, "STOCKITEMNAME", item.description[:100])
        if item.hsn_sac_code:
            _add_text(inv_entry, "HSNCODE", item.hsn_sac_code)
        if item.quantity:
            _add_text(inv_entry, "ACTUALQTY", f"{item.quantity}")
        _add_text(inv_entry, "AMOUNT", f"-{_fmt_amount(item.amount)}")
        if item.gst_rate:
            _add_text(inv_entry, "GSTRATE", f"{item.gst_rate}")


def generate_sales_voucher(invoice: Invoice, client: Client) -> str:
    """Generate Tally XML for a sales invoice voucher."""
    envelope = Element("ENVELOPE")
    header = SubElement(envelope, "HEADER")
    _add_text(header, "TALLYREQUEST", "Import Data")

    body = SubElement(envelope, "BODY")
    import_data = SubElement(body, "IMPORTDATA")
    req_desc = SubElement(import_data, "REQUESTDESC")
    _add_text(req_desc, "REPORTNAME", "Vouchers")
    static_vars = SubElement(req_desc, "STATICVARIABLES")
    _add_text(static_vars, "SVCURRENTCOMPANY", "##COMPANY##")

    req_data = SubElement(import_data, "REQUESTDATA")
    tally_msg = SubElement(req_data, "TALLYMESSAGE")
    tally_msg.set("xmlns:UDF", "TallyUDF")

    voucher = SubElement(tally_msg, "VOUCHER")
    voucher.set("VCHTYPE", "Sales")
    voucher.set("ACTION", "Create")

    _add_text(voucher, "DATE", _fmt_date(invoice.invoice_date))
    _add_text(voucher, "VOUCHERTYPENAME", "Sales")
    _add_text(voucher, "VOUCHERNUMBER", invoice.invoice_number or "")
    _add_text(voucher, "NARRATION", f"Sales Invoice {invoice.invoice_number or ''}")

    # Party ledger (buyer)
    party_name = invoice.buyer_name or "Cash"
    _add_text(voucher, "PARTYNAME", party_name)
    _add_text(voucher, "PARTYLEDGERNAME", party_name)

    # Party (debit) entry — the buyer owes us
    party_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(party_entry, "LEDGERNAME", party_name)
    _add_text(party_entry, "ISDEEMEDPOSITIVE", "Yes")
    _add_text(party_entry, "AMOUNT", _fmt_amount(invoice.total_amount))

    # Sales ledger (credit)
    sales_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(sales_entry, "LEDGERNAME", "Sales Account")
    _add_text(sales_entry, "ISDEEMEDPOSITIVE", "No")
    _add_text(sales_entry, "AMOUNT", f"-{_fmt_amount(invoice.taxable_amount)}")

    # GST
    _build_gst_allocation(voucher, invoice)

    # GSTIN info
    if invoice.buyer_gstin:
        _add_text(voucher, "PARTYGSTIN", invoice.buyer_gstin)
    if client.gstin:
        _add_text(voucher, "GSTIN", client.gstin)
    if invoice.place_of_supply:
        _add_text(voucher, "PLACEOFSUPPLY", invoice.place_of_supply)

    # Inventory entries
    if invoice.line_items:
        _build_inventory_entries(voucher, invoice.line_items)

    return tostring(envelope, encoding="unicode", xml_declaration=True)


def generate_purchase_voucher(invoice: Invoice, client: Client) -> str:
    """Generate Tally XML for a purchase invoice voucher."""
    envelope = Element("ENVELOPE")
    header = SubElement(envelope, "HEADER")
    _add_text(header, "TALLYREQUEST", "Import Data")

    body = SubElement(envelope, "BODY")
    import_data = SubElement(body, "IMPORTDATA")
    req_desc = SubElement(import_data, "REQUESTDESC")
    _add_text(req_desc, "REPORTNAME", "Vouchers")
    static_vars = SubElement(req_desc, "STATICVARIABLES")
    _add_text(static_vars, "SVCURRENTCOMPANY", "##COMPANY##")

    req_data = SubElement(import_data, "REQUESTDATA")
    tally_msg = SubElement(req_data, "TALLYMESSAGE")
    tally_msg.set("xmlns:UDF", "TallyUDF")

    voucher = SubElement(tally_msg, "VOUCHER")
    voucher.set("VCHTYPE", "Purchase")
    voucher.set("ACTION", "Create")

    _add_text(voucher, "DATE", _fmt_date(invoice.invoice_date))
    _add_text(voucher, "VOUCHERTYPENAME", "Purchase")
    _add_text(voucher, "VOUCHERNUMBER", invoice.invoice_number or "")
    _add_text(voucher, "NARRATION", f"Purchase Invoice {invoice.invoice_number or ''}")

    # Party ledger (seller)
    party_name = invoice.seller_name or "Cash"
    _add_text(voucher, "PARTYNAME", party_name)
    _add_text(voucher, "PARTYLEDGERNAME", party_name)

    # Party (credit) entry — we owe the seller
    party_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(party_entry, "LEDGERNAME", party_name)
    _add_text(party_entry, "ISDEEMEDPOSITIVE", "No")
    _add_text(party_entry, "AMOUNT", f"-{_fmt_amount(invoice.total_amount)}")

    # Purchase ledger (debit)
    purchase_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(purchase_entry, "LEDGERNAME", "Purchase Account")
    _add_text(purchase_entry, "ISDEEMEDPOSITIVE", "Yes")
    _add_text(purchase_entry, "AMOUNT", _fmt_amount(invoice.taxable_amount))

    # GST (debit — ITC)
    if invoice.cgst_amount and invoice.cgst_amount > 0:
        ledger = SubElement(voucher, "LEDGERENTRIES.LIST")
        _add_text(ledger, "LEDGERNAME", "CGST Input")
        _add_text(ledger, "ISDEEMEDPOSITIVE", "Yes")
        _add_text(ledger, "AMOUNT", _fmt_amount(invoice.cgst_amount))

    if invoice.sgst_amount and invoice.sgst_amount > 0:
        ledger = SubElement(voucher, "LEDGERENTRIES.LIST")
        _add_text(ledger, "LEDGERNAME", "SGST Input")
        _add_text(ledger, "ISDEEMEDPOSITIVE", "Yes")
        _add_text(ledger, "AMOUNT", _fmt_amount(invoice.sgst_amount))

    if invoice.igst_amount and invoice.igst_amount > 0:
        ledger = SubElement(voucher, "LEDGERENTRIES.LIST")
        _add_text(ledger, "LEDGERNAME", "IGST Input")
        _add_text(ledger, "ISDEEMEDPOSITIVE", "Yes")
        _add_text(ledger, "AMOUNT", _fmt_amount(invoice.igst_amount))

    # GSTIN info
    if invoice.seller_gstin:
        _add_text(voucher, "PARTYGSTIN", invoice.seller_gstin)
    if client.gstin:
        _add_text(voucher, "GSTIN", client.gstin)
    if invoice.place_of_supply:
        _add_text(voucher, "PLACEOFSUPPLY", invoice.place_of_supply)

    # Inventory entries
    if invoice.line_items:
        _build_inventory_entries(voucher, invoice.line_items)

    return tostring(envelope, encoding="unicode", xml_declaration=True)


def generate_payment_voucher(match: ReconciliationMatch, invoice: Invoice, txn: Transaction) -> str:
    """Generate Tally XML for a payment voucher (purchase paid)."""
    envelope = Element("ENVELOPE")
    header = SubElement(envelope, "HEADER")
    _add_text(header, "TALLYREQUEST", "Import Data")

    body = SubElement(envelope, "BODY")
    import_data = SubElement(body, "IMPORTDATA")
    req_desc = SubElement(import_data, "REQUESTDESC")
    _add_text(req_desc, "REPORTNAME", "Vouchers")
    static_vars = SubElement(req_desc, "STATICVARIABLES")
    _add_text(static_vars, "SVCURRENTCOMPANY", "##COMPANY##")

    req_data = SubElement(import_data, "REQUESTDATA")
    tally_msg = SubElement(req_data, "TALLYMESSAGE")
    tally_msg.set("xmlns:UDF", "TallyUDF")

    voucher = SubElement(tally_msg, "VOUCHER")
    voucher.set("VCHTYPE", "Payment")
    voucher.set("ACTION", "Create")

    _add_text(voucher, "DATE", _fmt_date(txn.transaction_date))
    _add_text(voucher, "VOUCHERTYPENAME", "Payment")
    _add_text(voucher, "NARRATION", f"Payment for {invoice.invoice_number or 'Invoice'} | {txn.raw_description[:80]}")

    party_name = invoice.seller_name or "Cash"
    amount = _fmt_amount(match.matched_amount)

    # Party (debit) — reduce payable
    party_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(party_entry, "LEDGERNAME", party_name)
    _add_text(party_entry, "ISDEEMEDPOSITIVE", "Yes")
    _add_text(party_entry, "AMOUNT", amount)

    # Bank (credit)
    bank_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(bank_entry, "LEDGERNAME", "Bank Account")
    _add_text(bank_entry, "ISDEEMEDPOSITIVE", "No")
    _add_text(bank_entry, "AMOUNT", f"-{amount}")

    return tostring(envelope, encoding="unicode", xml_declaration=True)


def generate_receipt_voucher(match: ReconciliationMatch, invoice: Invoice, txn: Transaction) -> str:
    """Generate Tally XML for a receipt voucher (sales payment received)."""
    envelope = Element("ENVELOPE")
    header = SubElement(envelope, "HEADER")
    _add_text(header, "TALLYREQUEST", "Import Data")

    body = SubElement(envelope, "BODY")
    import_data = SubElement(body, "IMPORTDATA")
    req_desc = SubElement(import_data, "REQUESTDESC")
    _add_text(req_desc, "REPORTNAME", "Vouchers")
    static_vars = SubElement(req_desc, "STATICVARIABLES")
    _add_text(static_vars, "SVCURRENTCOMPANY", "##COMPANY##")

    req_data = SubElement(import_data, "REQUESTDATA")
    tally_msg = SubElement(req_data, "TALLYMESSAGE")
    tally_msg.set("xmlns:UDF", "TallyUDF")

    voucher = SubElement(tally_msg, "VOUCHER")
    voucher.set("VCHTYPE", "Receipt")
    voucher.set("ACTION", "Create")

    _add_text(voucher, "DATE", _fmt_date(txn.transaction_date))
    _add_text(voucher, "VOUCHERTYPENAME", "Receipt")
    _add_text(voucher, "NARRATION", f"Receipt for {invoice.invoice_number or 'Invoice'} | {txn.raw_description[:80]}")

    party_name = invoice.buyer_name or "Cash"
    amount = _fmt_amount(match.matched_amount)

    # Bank (debit) — money received
    bank_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(bank_entry, "LEDGERNAME", "Bank Account")
    _add_text(bank_entry, "ISDEEMEDPOSITIVE", "Yes")
    _add_text(bank_entry, "AMOUNT", amount)

    # Party (credit) — reduce receivable
    party_entry = SubElement(voucher, "LEDGERENTRIES.LIST")
    _add_text(party_entry, "LEDGERNAME", party_name)
    _add_text(party_entry, "ISDEEMEDPOSITIVE", "No")
    _add_text(party_entry, "AMOUNT", f"-{amount}")

    return tostring(envelope, encoding="unicode", xml_declaration=True)


def generate_batch_xml(vouchers: list[str]) -> str:
    """Wrap multiple voucher XMLs in a single Tally import envelope."""
    envelope = Element("ENVELOPE")
    header = SubElement(envelope, "HEADER")
    _add_text(header, "TALLYREQUEST", "Import Data")

    body = SubElement(envelope, "BODY")
    import_data = SubElement(body, "IMPORTDATA")
    req_desc = SubElement(import_data, "REQUESTDESC")
    _add_text(req_desc, "REPORTNAME", "Vouchers")
    static_vars = SubElement(req_desc, "STATICVARIABLES")
    _add_text(static_vars, "SVCURRENTCOMPANY", "##COMPANY##")

    req_data = SubElement(import_data, "REQUESTDATA")

    # Concatenate all voucher bodies — we re-parse each to extract TALLYMESSAGE
    from xml.etree.ElementTree import fromstring
    for xml_str in vouchers:
        try:
            parsed = fromstring(xml_str)
            tally_msgs = parsed.findall(".//TALLYMESSAGE")
            for msg in tally_msgs:
                req_data.append(msg)
        except Exception:
            continue

    return tostring(envelope, encoding="unicode", xml_declaration=True)


def generate_ledger_xml(client: Client) -> str:
    """Generate XML to create party ledgers in Tally for the client."""
    envelope = Element("ENVELOPE")
    header = SubElement(envelope, "HEADER")
    _add_text(header, "TALLYREQUEST", "Import Data")

    body = SubElement(envelope, "BODY")
    import_data = SubElement(body, "IMPORTDATA")
    req_desc = SubElement(import_data, "REQUESTDESC")
    _add_text(req_desc, "REPORTNAME", "All Masters")
    static_vars = SubElement(req_desc, "STATICVARIABLES")
    _add_text(static_vars, "SVCURRENTCOMPANY", "##COMPANY##")

    req_data = SubElement(import_data, "REQUESTDATA")
    tally_msg = SubElement(req_data, "TALLYMESSAGE")
    tally_msg.set("xmlns:UDF", "TallyUDF")

    ledger = SubElement(tally_msg, "LEDGER")
    ledger.set("NAME", client.business_name)
    ledger.set("ACTION", "Create")

    _add_text(ledger, "NAME", client.business_name)
    _add_text(ledger, "PARENT", "Sundry Debtors")
    if client.gstin:
        _add_text(ledger, "PARTYGSTIN", client.gstin)
    if client.address:
        _add_text(ledger, "ADDRESS", client.address)
    if client.state_code:
        _add_text(ledger, "LEDSTATENAME", client.state_code)

    return tostring(envelope, encoding="unicode", xml_declaration=True)
