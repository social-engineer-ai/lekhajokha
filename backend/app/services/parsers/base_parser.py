from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class RawTransaction:
    transaction_date: date
    value_date: date | None
    description: str
    reference_number: str | None
    cheque_ref_no: str | None
    amount: Decimal
    transaction_type: str  # "debit" or "credit"
    running_balance: Decimal | None


class BaseBankParser(ABC):
    """Abstract base class for bank statement parsers."""

    @abstractmethod
    def parse(self, tables: list[list[list[str | None]]]) -> list[RawTransaction]:
        """Parse extracted PDF tables into a list of RawTransaction."""
        ...

    def _parse_amount(self, value: str | None) -> Decimal | None:
        """Clean and parse a monetary value string."""
        if not value:
            return None
        cleaned = value.strip().replace(",", "").replace(" ", "")
        if not cleaned or cleaned == "-" or cleaned.lower() == "nil":
            return None
        try:
            return Decimal(cleaned)
        except Exception:
            return None

    def _clean_cell(self, value: str | None) -> str:
        """Clean a table cell value."""
        if value is None:
            return ""
        return " ".join(value.split()).strip()
