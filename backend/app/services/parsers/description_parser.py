import re
from dataclasses import dataclass


@dataclass
class ParsedDescription:
    mode: str | None = None  # NEFT, UPI, IMPS, RTGS, ACH, INTERNAL, CASH, CHEQUE, ATM
    counterparty: str | None = None
    bank_ifsc: str | None = None
    upi_id: str | None = None
    reference: str | None = None


# Patterns for transaction mode detection and field extraction
_NEFT_PATTERN = re.compile(
    r"NEFT[/-]?(?:CR|DR)?[/-]?(?P<ifsc>[A-Z]{4}0[A-Z0-9]{6})[/-](?P<counterparty>.+?)(?:[/-](?P<ref>\d+))?$",
    re.IGNORECASE,
)
_NEFT_SIMPLE = re.compile(r"NEFT[/-]", re.IGNORECASE)

_UPI_PATTERN = re.compile(
    r"UPI[/-](?P<ref>\d+)[/-](?P<counterparty>[^/]+)[/-](?P<upi_id>\S+@\S+)",
    re.IGNORECASE,
)
_UPI_NO_ID_PATTERN = re.compile(
    r"UPI[/-](?P<ref>\d+)[/-](?P<counterparty>[^/]+)$",
    re.IGNORECASE,
)
_UPI_SIMPLE = re.compile(r"UPI[/-]|UPI\s", re.IGNORECASE)

_IMPS_PATTERN = re.compile(
    r"IMPS[/-](?P<ref>\d+)[/-](?P<counterparty>.+?)(?:[/-](?P<ifsc>[A-Z]{4}0[A-Z0-9]{6}))?$",
    re.IGNORECASE,
)
_IMPS_SIMPLE = re.compile(r"IMPS[/-]", re.IGNORECASE)

_RTGS_PATTERN = re.compile(
    r"RTGS[/-](?P<ifsc>[A-Z]{4}0[A-Z0-9]{6})[/-](?P<counterparty>.+?)(?:[/-](?P<ref>\S+))?$",
    re.IGNORECASE,
)
_RTGS_SIMPLE = re.compile(r"RTGS[/-]", re.IGNORECASE)

_ACH_PATTERN = re.compile(
    r"(?:NACH|ACH)[/-](?:CR|DR)?[/-]?(?P<counterparty>.+?)(?:[/-](?P<ref>\S+))?$",
    re.IGNORECASE,
)
_ACH_SIMPLE = re.compile(r"(?:NACH|ACH)[/-]", re.IGNORECASE)

_CHEQUE_PATTERN = re.compile(r"(?:CHQ|CHEQUE|CLG)[/-]?(?P<ref>\d+)", re.IGNORECASE)
_ATM_PATTERN = re.compile(r"ATM[/-]|ATM\s|CASH\sWITHDRAWAL", re.IGNORECASE)
_INTERNAL_PATTERN = re.compile(r"(?:INT\.?|INTEREST|FD\s|SWEEP|TRF\s|TRANSFER)", re.IGNORECASE)

_UPI_ID_EXTRACT = re.compile(r"(\S+@\S+)")
_IFSC_EXTRACT = re.compile(r"([A-Z]{4}0[A-Z0-9]{6})")


def parse_description(raw: str) -> ParsedDescription:
    """Parse a bank transaction description to extract mode, counterparty, IFSC, UPI ID, reference."""
    if not raw:
        return ParsedDescription()

    text = raw.strip()

    # Try NEFT
    m = _NEFT_PATTERN.search(text)
    if m:
        return ParsedDescription(
            mode="NEFT",
            counterparty=_clean(m.group("counterparty")),
            bank_ifsc=m.group("ifsc"),
            reference=m.group("ref"),
        )
    if _NEFT_SIMPLE.search(text):
        ifsc_m = _IFSC_EXTRACT.search(text)
        return ParsedDescription(
            mode="NEFT",
            counterparty=_extract_counterparty_fallback(text, "NEFT"),
            bank_ifsc=ifsc_m.group(1) if ifsc_m else None,
        )

    # Try UPI (with UPI ID)
    m = _UPI_PATTERN.search(text)
    if m:
        return ParsedDescription(
            mode="UPI",
            counterparty=_clean(m.group("counterparty")),
            upi_id=m.group("upi_id"),
            reference=m.group("ref"),
        )
    # Try UPI (without UPI ID)
    m = _UPI_NO_ID_PATTERN.search(text)
    if m:
        upi_m = _UPI_ID_EXTRACT.search(text)
        return ParsedDescription(
            mode="UPI",
            counterparty=_clean(m.group("counterparty")),
            upi_id=upi_m.group(1) if upi_m else None,
            reference=m.group("ref"),
        )
    if _UPI_SIMPLE.search(text):
        upi_m = _UPI_ID_EXTRACT.search(text)
        return ParsedDescription(
            mode="UPI",
            counterparty=_extract_counterparty_fallback(text, "UPI"),
            upi_id=upi_m.group(1) if upi_m else None,
        )

    # Try IMPS
    m = _IMPS_PATTERN.search(text)
    if m:
        return ParsedDescription(
            mode="IMPS",
            counterparty=_clean(m.group("counterparty")),
            bank_ifsc=m.group("ifsc"),
            reference=m.group("ref"),
        )
    if _IMPS_SIMPLE.search(text):
        ifsc_m = _IFSC_EXTRACT.search(text)
        return ParsedDescription(
            mode="IMPS",
            counterparty=_extract_counterparty_fallback(text, "IMPS"),
            bank_ifsc=ifsc_m.group(1) if ifsc_m else None,
        )

    # Try RTGS
    m = _RTGS_PATTERN.search(text)
    if m:
        return ParsedDescription(
            mode="RTGS",
            counterparty=_clean(m.group("counterparty")),
            bank_ifsc=m.group("ifsc"),
            reference=m.group("ref"),
        )
    if _RTGS_SIMPLE.search(text):
        ifsc_m = _IFSC_EXTRACT.search(text)
        return ParsedDescription(
            mode="RTGS",
            counterparty=_extract_counterparty_fallback(text, "RTGS"),
            bank_ifsc=ifsc_m.group(1) if ifsc_m else None,
        )

    # Try ACH/NACH
    m = _ACH_PATTERN.search(text)
    if m:
        return ParsedDescription(
            mode="ACH",
            counterparty=_clean(m.group("counterparty")),
            reference=m.group("ref"),
        )
    if _ACH_SIMPLE.search(text):
        return ParsedDescription(
            mode="ACH",
            counterparty=_extract_counterparty_fallback(text, "ACH"),
        )

    # Try cheque
    m = _CHEQUE_PATTERN.search(text)
    if m:
        return ParsedDescription(mode="CHEQUE", reference=m.group("ref"))

    # Try ATM
    if _ATM_PATTERN.search(text):
        return ParsedDescription(mode="ATM")

    # Try internal/transfer
    if _INTERNAL_PATTERN.search(text):
        return ParsedDescription(mode="INTERNAL", counterparty=_clean(text))

    # No pattern matched
    return ParsedDescription()


def _clean(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().strip("/-")
    return s if s else None


def _extract_counterparty_fallback(text: str, mode: str) -> str | None:
    """Try to extract counterparty from text after removing the mode prefix."""
    parts = re.split(rf"{mode}[/-]?\s*", text, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) > 1:
        remaining = parts[1].strip()
        # Take first meaningful segment
        segments = re.split(r"[/\-]", remaining)
        for seg in segments:
            seg = seg.strip()
            if seg and not seg.isdigit() and len(seg) > 2:
                return seg
    return None
