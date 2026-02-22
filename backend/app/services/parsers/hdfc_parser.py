import logging
from datetime import datetime, date
from decimal import Decimal

from app.services.parsers.base_parser import BaseBankParser, RawTransaction

logger = logging.getLogger(__name__)

# HDFC format:
# Columns: Date | Narration | Chq./Ref.No. | Value Dt | Withdrawal Amt. | Deposit Amt. | Closing Balance
# Date format: DD/MM/YY or DD/MM/YYYY


class HDFCParser(BaseBankParser):
    DATE_FORMATS = ["%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y"]

    def parse(self, tables: list[list[list[str | None]]]) -> list[RawTransaction]:
        transactions = []
        for table in tables:
            header_idx = self._find_header_row(table)
            if header_idx is None:
                continue
            col_map = self._map_columns(table[header_idx])
            for row in table[header_idx + 1:]:
                txn = self._parse_row(row, col_map)
                if txn:
                    transactions.append(txn)
        return transactions

    def _find_header_row(self, table: list[list[str | None]]) -> int | None:
        for i, row in enumerate(table):
            cells = [self._clean_cell(c).lower() for c in row]
            joined = " ".join(cells)
            if "narration" in joined and ("withdrawal" in joined or "deposit" in joined):
                return i
            if "date" in joined and ("withdrawal" in joined or "debit" in joined):
                return i
        return None

    def _map_columns(self, header: list[str | None]) -> dict[str, int]:
        col_map = {}
        for i, cell in enumerate(header):
            c = self._clean_cell(cell).lower()
            if "value" in c and "dt" in c:
                col_map["value_date"] = i
            elif "date" in c and "value" not in c and "txn_date" not in col_map:
                col_map["txn_date"] = i
            elif "narration" in c or "description" in c or "particular" in c:
                col_map["description"] = i
            elif "chq" in c or "ref" in c:
                col_map["cheque"] = i
            elif ("withdrawal" in c or "debit" in c or "dr" in c) and "balance" not in c and "debit" not in col_map:
                col_map["debit"] = i
            elif ("deposit" in c or "credit" in c or "cr" in c) and "balance" not in c and "credit" not in col_map:
                col_map["credit"] = i
            elif "balance" in c or "closing" in c:
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
            txn_date = self._parse_date(txn_date_str)
            if not txn_date:
                return None

            value_date = None
            if "value_date" in col_map:
                value_date = self._parse_date(self._clean_cell(row[col_map["value_date"]]))

            description = self._clean_cell(row[col_map.get("description", 1)])
            if not description:
                return None

            cheque = self._clean_cell(row[col_map["cheque"]]) if "cheque" in col_map else None

            debit = self._parse_amount(row[col_map["debit"]]) if "debit" in col_map else None
            credit = self._parse_amount(row[col_map["credit"]]) if "credit" in col_map else None
            balance = self._parse_amount(row[col_map["balance"]]) if "balance" in col_map else None

            if debit and debit > 0:
                amount = debit
                txn_type = "debit"
            elif credit and credit > 0:
                amount = credit
                txn_type = "credit"
            else:
                return None

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

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return None
