import re
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


@dataclass
class ParsedLineItem:
    line_number: int
    description: str
    hsn_sac_code: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    amount: Decimal = Decimal("0")
    gst_rate: Decimal | None = None


@dataclass
class ParsedInvoice:
    invoice_number: str | None = None
    invoice_date: date | None = None
    seller_name: str | None = None
    seller_gstin: str | None = None
    buyer_name: str | None = None
    buyer_gstin: str | None = None
    place_of_supply: str | None = None
    taxable_amount: Decimal | None = None
    cgst_amount: Decimal | None = None
    sgst_amount: Decimal | None = None
    igst_amount: Decimal | None = None
    total_tax: Decimal | None = None
    total_amount: Decimal | None = None
    line_items: list[ParsedLineItem] = field(default_factory=list)
    confidence: float = 0.0


# GSTIN: 2 digits + 5 uppercase + 4 digits + 1 uppercase + 1 alphanumeric + Z + 1 alphanumeric
GSTIN_PATTERN = re.compile(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b')

# HSN/SAC codes: 4, 6, or 8 digit numbers near "HSN" keyword
HSN_PATTERN = re.compile(r'\b(\d{4}(?:\d{2})?(?:\d{2})?)\b')

# Common Indian date formats
DATE_PATTERNS = [
    re.compile(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})'),  # DD/MM/YYYY or DD-MM-YYYY
    re.compile(r'(\d{1,2})[/\-.\s]+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[/\-.\s]+(\d{4})', re.IGNORECASE),
]

MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}


def parse_invoice_text(text: str) -> ParsedInvoice:
    """Main entry point: parse OCR text into structured invoice data."""
    result = ParsedInvoice()

    gstins = _extract_gstins(text)
    if len(gstins) >= 2:
        result.seller_gstin = gstins[0]
        result.buyer_gstin = gstins[1]
    elif len(gstins) == 1:
        result.seller_gstin = gstins[0]

    result.invoice_number = _extract_invoice_number(text)
    result.invoice_date = _extract_invoice_date(text)
    result.place_of_supply = _extract_place_of_supply(text)
    result.seller_name = _extract_name_near_gstin(text, result.seller_gstin, position="first")
    result.buyer_name = _extract_buyer_name(text)

    amounts = _extract_amounts(text)
    result.taxable_amount = amounts.get("taxable")
    result.cgst_amount = amounts.get("cgst")
    result.sgst_amount = amounts.get("sgst")
    result.igst_amount = amounts.get("igst")
    result.total_tax = amounts.get("total_tax")
    result.total_amount = amounts.get("total")

    result.line_items = _extract_line_items(text)

    return result


def detect_invoice_type(seller_gstin: str | None, client_gstin: str | None) -> str:
    """If seller_gstin matches client's GSTIN, it's a sales invoice. Otherwise purchase."""
    if seller_gstin and client_gstin:
        if seller_gstin.upper() == client_gstin.upper():
            return "sales"
        return "purchase"
    return "purchase"  # default to purchase if we can't determine


def _extract_gstins(text: str) -> list[str]:
    """Extract all unique GSTINs from text, preserving order of appearance."""
    matches = GSTIN_PATTERN.findall(text)
    seen = set()
    unique = []
    for g in matches:
        if g not in seen:
            seen.add(g)
            unique.append(g)
    return unique


def _extract_invoice_number(text: str) -> str | None:
    """Extract invoice number from common patterns."""
    patterns = [
        re.compile(r'(?:Invoice\s*No|Inv\.?\s*No|Bill\s*No|Tax\s*Invoice\s*No|Invoice\s*#|Inv\s*#)[.:;\s]*([A-Za-z0-9/\-_]+(?:[/\-][A-Za-z0-9]+)*)', re.IGNORECASE),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_invoice_date(text: str) -> date | None:
    """Extract invoice date from text."""
    # First try to find date near "Invoice Date" or "Date:" labels
    date_label_pattern = re.compile(
        r'(?:Invoice\s*Date|Date\s*of\s*Invoice|Inv\.?\s*Date|Bill\s*Date|Date)[:\s]+(.{10,30})',
        re.IGNORECASE
    )
    label_match = date_label_pattern.search(text)
    search_text = label_match.group(1) if label_match else text

    # Try DD/MM/YYYY or DD-MM-YYYY
    m = DATE_PATTERNS[0].search(search_text)
    if m:
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(year, month, day)
        except ValueError:
            pass

    # Try DD-Mon-YYYY
    m = DATE_PATTERNS[1].search(search_text)
    if m:
        try:
            day = int(m.group(1))
            month = MONTH_MAP.get(m.group(2).lower()[:3], 0)
            year = int(m.group(3))
            if month:
                return date(year, month, day)
        except ValueError:
            pass

    # Fallback: search entire text if label search failed
    if label_match:
        return _extract_invoice_date_from_text(text)

    return None


def _extract_invoice_date_from_text(text: str) -> date | None:
    """Fallback date extraction from entire text."""
    m = DATE_PATTERNS[0].search(text)
    if m:
        try:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(year, month, day)
        except ValueError:
            pass
    return None


def _extract_place_of_supply(text: str) -> str | None:
    """Extract place of supply."""
    pattern = re.compile(r'Place\s*of\s*Supply[:\s]+(.+?)(?:\n|$)', re.IGNORECASE)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()[:100]
    return None


def _extract_name_near_gstin(text: str, gstin: str | None, position: str = "first") -> str | None:
    """Extract company name near a GSTIN. Usually the line(s) above the GSTIN."""
    if not gstin:
        return None
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if gstin in line:
            # Look at preceding non-empty lines for company name
            for j in range(i - 1, max(i - 5, -1), -1):
                candidate = lines[j].strip()
                # Skip empty lines, headers, and short labels
                if candidate and len(candidate) > 3 and not re.match(r'^(TAX\s*INVOICE|INVOICE|ORIGINAL|DUPLICATE|Bill\s*To|Ship\s*To|Sold\s*To)', candidate, re.IGNORECASE):
                    return candidate[:255]
            break
    return None


def _extract_buyer_name(text: str) -> str | None:
    """Extract buyer name from Bill To / Sold To section."""
    pattern = re.compile(
        r'(?:Bill\s*To|Sold\s*To|Buyer|Ship\s*To|Customer)[:\s]*\n\s*(.+?)(?:\n|$)',
        re.IGNORECASE
    )
    m = pattern.search(text)
    if m:
        name = m.group(1).strip()
        if name and len(name) > 2:
            return name[:255]
    return None


def _parse_amount(text: str) -> Decimal | None:
    """Parse an amount string like '1,46,500.00' into a Decimal."""
    # Remove commas and whitespace
    cleaned = re.sub(r'[,\s]', '', text.strip())
    # Remove currency symbols (Rs., ₹, $, INR)
    cleaned = re.sub(r'Rs\.?|INR|[₹$]', '', cleaned, flags=re.IGNORECASE).strip()
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _extract_amounts(text: str) -> dict[str, Decimal | None]:
    """Extract tax and total amounts from text."""
    result: dict[str, Decimal | None] = {}

    patterns = {
        "taxable": re.compile(r'(?:Taxable\s*(?:Value|Amount)|Sub\s*Total|Net\s*Amount)[:\s]*[₹Rs.\s]*([\d,]+\.?\d*)', re.IGNORECASE),
        "cgst": re.compile(r'CGST(?:\s*@?\s*\d+%)?[^₹\d]*[₹Rs.\s]*([\d,]+\.?\d*)', re.IGNORECASE),
        "sgst": re.compile(r'SGST(?:\s*@?\s*\d+%)?[^₹\d]*[₹Rs.\s]*([\d,]+\.?\d*)', re.IGNORECASE),
        "igst": re.compile(r'IGST(?:\s*@?\s*\d+%)?[^₹\d]*[₹Rs.\s]*([\d,]+\.?\d*)', re.IGNORECASE),
        "total_tax": re.compile(r'Total\s*Tax[:\s]*[₹Rs.\s]*([\d,]+\.?\d*)', re.IGNORECASE),
        "total": re.compile(r'(?:Grand\s*Total|Total\s*Amount|Invoice\s*Total|Total\s*(?:Value)?)[:\s]*[₹Rs.\s]*([\d,]+\.?\d*)', re.IGNORECASE),
    }

    for key, pattern in patterns.items():
        m = pattern.search(text)
        if m:
            result[key] = _parse_amount(m.group(1))

    return result


def _extract_line_items(text: str) -> list[ParsedLineItem]:
    """Extract line items from table-like rows in the text.
    Heuristic: look for rows starting with a sequential number followed by description and amounts.
    """
    items = []

    # Pattern: line number | description | optional HSN | optional qty | optional unit | optional rate | amount
    # We look for lines starting with a digit (line number) followed by text and at least one number (amount)
    line_pattern = re.compile(
        r'^\s*(\d{1,3})\s*[|\s]+(.+?)\s*$',
        re.MULTILINE
    )

    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Match lines starting with a small number (line item number)
        m = re.match(r'^\s*(\d{1,3})\s*[|.\s]\s*(.+)', line_stripped)
        if not m:
            continue

        line_num = int(m.group(1))
        if line_num < 1 or line_num > 999:
            continue

        rest = m.group(2)

        # Try to find amounts in this line (numbers with commas/decimals at the end)
        amount_matches = list(re.finditer(r'([\d,]+\.\d{2})', rest))
        if not amount_matches:
            continue

        # Last amount is the line total
        last_amount = _parse_amount(amount_matches[-1].group(1))
        if last_amount is None or last_amount <= 0:
            continue

        # Extract description (text before first number cluster)
        desc_end = amount_matches[0].start() if amount_matches else len(rest)
        # Remove any HSN-like codes, qty, unit from the description part
        desc_part = rest[:desc_end].strip().rstrip('|').strip()

        # Try to find HSN code (4-8 digit number)
        hsn = None
        hsn_match = re.search(r'\b(\d{4}(?:\d{2})?(?:\d{2})?)\b', rest)
        if hsn_match:
            candidate = hsn_match.group(1)
            # Ensure it looks like an HSN (not a quantity or price)
            if len(candidate) >= 4 and int(candidate) > 1000:
                hsn = candidate
                # Remove HSN from description
                desc_part = desc_part.replace(candidate, '').strip()

        # Try to extract quantity and unit
        qty = None
        unit = None
        unit_price = None
        qty_match = re.search(r'\b(\d+(?:\.\d+)?)\s*(Nos|Pcs|Kgs|Kg|Ltrs|Ltr|Mtr|Sqft|Sqm|Set|Box|Pair|Unit|Bag|Roll|Pack)\b', rest, re.IGNORECASE)
        if qty_match:
            try:
                qty = Decimal(qty_match.group(1))
                unit = qty_match.group(2)
            except (InvalidOperation, ValueError):
                pass

        # If we have qty and multiple amounts, second-to-last might be unit price
        if qty and len(amount_matches) >= 2:
            unit_price = _parse_amount(amount_matches[-2].group(1))

        # Clean up description
        desc_part = re.sub(r'\s+', ' ', desc_part).strip()
        if not desc_part or len(desc_part) < 2:
            desc_part = f"Item {line_num}"

        item = ParsedLineItem(
            line_number=line_num,
            description=desc_part,
            hsn_sac_code=hsn,
            quantity=qty,
            unit=unit,
            unit_price=unit_price,
            amount=last_amount,
        )
        items.append(item)

    return items
