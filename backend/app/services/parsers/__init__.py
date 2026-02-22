from app.services.parsers.base_parser import BaseBankParser
from app.services.parsers.icici_parser import ICICIParser
from app.services.parsers.hdfc_parser import HDFCParser
from app.services.parsers.sbi_parser import SBIParser
from app.services.parsers.axis_parser import AxisParser
from app.services.parsers.kotak_parser import KotakParser
from app.services.parsers.generic_parser import GenericParser

PARSER_MAP: dict[str, BaseBankParser] = {
    "icici": ICICIParser(),
    "hdfc": HDFCParser(),
    "sbi": SBIParser(),
    "axis": AxisParser(),
    "kotak": KotakParser(),
}


def get_parser(bank_key: str | None) -> BaseBankParser:
    """Get a bank-specific parser or fall back to the generic parser."""
    if bank_key and bank_key in PARSER_MAP:
        return PARSER_MAP[bank_key]
    return GenericParser()
