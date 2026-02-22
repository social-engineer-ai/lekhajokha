import io
import logging
import tempfile

import pikepdf
import pdfplumber

logger = logging.getLogger(__name__)


def is_pdf_encrypted(pdf_bytes: bytes) -> bool:
    """Check if PDF is encrypted / password-protected."""
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
            return False
    except pikepdf.PasswordError:
        return True


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """Decrypt a password-protected PDF. Returns decrypted PDF bytes."""
    with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
        output = io.BytesIO()
        pdf.save(output)
        return output.getvalue()


def extract_tables(pdf_bytes: bytes) -> list[list[list[str | None]]]:
    """Extract all tables from all pages of a PDF.
    Returns a list of tables, where each table is a list of rows,
    and each row is a list of cell values.
    """
    all_tables = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                all_tables.extend(tables)
    return all_tables


def extract_text(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF for bank detection."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n".join(text_parts)
