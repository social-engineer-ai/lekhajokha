import re
import logging

logger = logging.getLogger(__name__)

# Keyword patterns for detecting bank from PDF text
_BANK_PATTERNS = {
    "icici": [r"ICICI\s*Bank", r"Industrial\s+Credit"],
    "hdfc": [r"HDFC\s*Bank", r"HDFC\s*Ltd"],
    "sbi": [r"State\s+Bank\s+of\s+India", r"\bSBI\b"],
    "axis": [r"Axis\s*Bank"],
    "kotak": [r"Kotak\s*Mahindra", r"Kotak\s*Bank"],
    "pnb": [r"Punjab\s+National\s+Bank", r"\bPNB\b"],
    "bob": [r"Bank\s+of\s+Baroda", r"\bBOB\b"],
    "canara": [r"Canara\s+Bank"],
    "union": [r"Union\s+Bank\s+of\s+India"],
    "idbi": [r"IDBI\s*Bank"],
    "yes": [r"Yes\s*Bank"],
    "indusind": [r"IndusInd\s*Bank"],
    "federal": [r"Federal\s*Bank"],
    "rbl": [r"RBL\s*Bank", r"Ratnakar\s+Bank"],
}

# Map common bank_name field values to parser keys
_BANK_NAME_MAP = {
    "icici bank": "icici",
    "hdfc bank": "hdfc",
    "state bank of india": "sbi",
    "sbi": "sbi",
    "axis bank": "axis",
    "kotak mahindra bank": "kotak",
    "kotak bank": "kotak",
    "punjab national bank": "pnb",
    "bank of baroda": "bob",
    "canara bank": "canara",
    "union bank of india": "union",
    "idbi bank": "idbi",
    "yes bank": "yes",
    "indusind bank": "indusind",
    "federal bank": "federal",
    "rbl bank": "rbl",
}


def detect_bank(text: str) -> str | None:
    """Detect bank from PDF text content using keyword matching.
    Returns a bank key like 'icici', 'hdfc', etc. or None.
    """
    for bank_key, patterns in _BANK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.info(f"Detected bank: {bank_key}")
                return bank_key
    return None


def detect_bank_from_name(bank_name: str) -> str | None:
    """Try to map a bank_name (from BankAccount model) to a parser key."""
    normalized = bank_name.strip().lower()
    if normalized in _BANK_NAME_MAP:
        return _BANK_NAME_MAP[normalized]
    # Partial match
    for name, key in _BANK_NAME_MAP.items():
        if name in normalized or normalized in name:
            return key
    return None
