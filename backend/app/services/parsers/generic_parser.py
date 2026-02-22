import re
import logging
from datetime import datetime, date
from decimal import Decimal

from app.services.parsers.base_parser import BaseBankParser, RawTransaction

logger = logging.getLogger(__name__)

# Common date patterns in Indian bank statements
_DATE_PATTERNS = [
    (r"\d{2}[-/]\w{3}[-/]\d{4}", "%d-%b-%Y"),  # DD-MMM-YYYY
    (r"\d{2}[-/]\w{3}[-/]\d{2}", "%d-%b-%y"),    # DD-MMM-YY
    (r"\d{2}/\d{2}/\d{4}", "%d/%m/%Y"),           # DD/MM/YYYY
    (r"\d{2}/\d{2}/\d{2}", "%d/%m/%y"),           # DD/MM/YY
    (r"\d{2}-\d{2}-\d{4}", "%d-%m-%Y"),           # DD-MM-YYYY
    (r"\d{2}-\d{2}-\d{2}", "%d-%m-%y"),           # DD-MM-YY
    (r"\d{2}\s\w{3}\s\d{4}", "%d %b %Y"),         # DD MMM YYYY
]


class GenericParser(BaseBankParser):
    """Heuristic-based fallback parser for unknown bank formats."""

    def parse(self, tables: list[list[list[str | None]]]) -> list[RawTransaction]:
        transactions = []
        for table in tables:
            header_idx = self._find_header_row(table)
            if header_idx is None:
                continue
            col_map = self._map_columns_generic(table[header_idx])
            if "txn_date" not in col_map:
                continue
            for row in table[header_idx + 1:]:
                txn = self._parse_row(row, col_map)
                if txn:
                    transactions.append(txn)
        return transactions

    def _find_header_row(self, table: list[list[str | None]]) -> int | None:
        for i, row in enumerate(table):
            cells = [self._clean_cell(c).lower() for c in row]
            joined = " ".join(cells)
            if "date" in joined and any(
                kw in joined for kw in ["debit", "credit", "withdrawal", "deposit", "dr", "cr", "amount"]
            ):
                return i
        return None

    def _map_columns_generic(self, header: list[str | None]) -> dict[str, int]:
        col_map = {}
        for i, cell in enumerate(header):
            c = self._clean_cell(cell).lower()
            if "value" in c and "date" in c:
                col_map["value_date"] = i
            elif "date" in c and "txn_date" not in col_map and "value_date" not in col_map:
                col_map["txn_date"] = i
            elif any(kw in c for kw in ["description", "particular", "narration", "remark"]):
                col_map["description"] = i
            elif any(kw in c for kw in ["chq", "cheque", "ref"]):
                col_map["cheque"] = i
            elif any(kw in c for kw in ["withdrawal", "debit", "dr"]) and "balance" not in c and "debit" not in col_map:
                col_map["debit"] = i
            elif any(kw in c for kw in ["deposit", "credit", "cr"]) and "balance" not in c and "credit" not in col_map:
                col_map["credit"] = i
            elif "amount" in c and "debit" not in col_map and "credit" not in col_map:
                col_map["amount"] = i
            elif "balance" in c:
                col_map["balance"] = i
        # Fallback: if debit found but no credit, next column is likely credit
        if "debit" in col_map and "credit" not in col_map:
            next_col = col_map["debit"] + 1
            balance_col = col_map.get("balance", len(header))
            if next_col < balance_col:
                col_map["credit"] = next_col
        return col_map

    def _parse_row(self, row: list[str | None], col_map: dict[str, int]) -> RawTransaction | None:
        try:
            txn_date_str = self._clean_cell(row[col_map.get("txn_date", 0)])
            txn_date = self._try_parse_date(txn_date_str)
            if not txn_date:
                return None

            value_date = None
            if "value_date" in col_map:
                value_date = self._try_parse_date(self._clean_cell(row[col_map["value_date"]]))

            description = self._clean_cell(row[col_map.get("description", 1)])
            if not description:
                return None

            cheque = self._clean_cell(row[col_map["cheque"]]) if "cheque" in col_map else None

            # Handle separate debit/credit columns or combined amount column
            if "debit" in col_map and "credit" in col_map:
                debit = self._parse_amount(row[col_map["debit"]])
                credit = self._parse_amount(row[col_map["credit"]])
                if debit and debit > 0:
                    amount = debit
                    txn_type = "debit"
                elif credit and credit > 0:
                    amount = credit
                    txn_type = "credit"
                else:
                    return None
            elif "amount" in col_map:
                amt = self._parse_amount(row[col_map["amount"]])
                if not amt:
                    return None
                # Try to determine type from description or other clues
                desc_lower = description.lower()
                if any(kw in desc_lower for kw in ["credit", "deposit", "cr"]):
                    txn_type = "credit"
                else:
                    txn_type = "debit"
                amount = abs(amt)
            else:
                return None

            balance = self._parse_amount(row[col_map["balance"]]) if "balance" in col_map else None

            return RawTransaction(
                transaction_date=txn_date,
                value_date=value_date,
                description=description,
                reference_number=cheque,
                cheque_ref_no=cheque if cheque else None,
                amount=amount,
                transaction_type=txn_type,
                running_balance=balance,
            )
        except (IndexError, KeyError):
            return None

    def _try_parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        for pattern, fmt in _DATE_PATTERNS:
            m = re.match(pattern, date_str.strip())
            if m:
                try:
                    return datetime.strptime(m.group(), fmt).date()
                except ValueError:
                    continue
        return None
