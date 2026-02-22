import logging
from datetime import datetime, date
from decimal import Decimal

from app.services.parsers.base_parser import BaseBankParser, RawTransaction

logger = logging.getLogger(__name__)

# ICICI format:
# Columns: S No. | Value Date | Transaction Date | Cheque Number | Transaction Remarks | Withdrawal Amount (Dr) | Deposit Amount (Cr) | Balance (INR)
# Date format: DD-MMM-YYYY (e.g., 15-Jan-2024) or DD/MM/YYYY


class ICICIParser(BaseBankParser):
    DATE_FORMATS = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%y"]

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
            if ("date" in joined and ("withdrawal" in joined or "debit" in joined or "dr" in joined)):
                return i
            if "transaction" in joined and "remarks" in joined:
                return i
        return None

    def _map_columns(self, header: list[str | None]) -> dict[str, int]:
        col_map = {}
        for i, cell in enumerate(header):
            c = self._clean_cell(cell).lower()
            if "value" in c and "date" in c:
                col_map["value_date"] = i
            elif ("transaction" in c or "txn" in c) and "date" in c:
                col_map["txn_date"] = i
            elif "date" in c and "txn_date" not in col_map and "value_date" not in col_map:
                col_map["txn_date"] = i
            elif "cheque" in c or "chq" in c:
                col_map["cheque"] = i
            elif "remark" in c or "description" in c or "particular" in c or "narration" in c:
                col_map["description"] = i
            elif ("withdrawal" in c or "dr" in c) and "balance" not in c and "debit" not in col_map:
                col_map["debit"] = i
            elif ("deposit" in c or "cr" in c) and "balance" not in c and "credit" not in col_map:
                col_map["credit"] = i
            elif "balance" in c:
                col_map["balance"] = i

        # Fallback: if debit found but no credit, and the next column after debit
        # is before balance, treat it as credit (handles mangled PDF headers)
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
                reference_number=None,
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
