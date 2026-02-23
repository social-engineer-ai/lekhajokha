"""OCR service for extracting text from invoice images and PDFs.

Supports multiple OCR backends controlled by OCR_ENGINE setting:
  - "paddleocr" (default) — self-hosted, no API key needed, best Indic accuracy
  - "google_vision"       — Google Cloud Vision API (requires GOOGLE_VISION_API_KEY)
  - "easyocr"             — self-hosted fallback (requires easyocr package)
  - "mock"                — returns sample invoice text for dev/testing

See docs/ocr-alternatives.md for full comparison and fine-tuning notes.
"""

import logging
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized engine singletons
_paddle_ocr = None
_easyocr_reader = None


# ── Public API (unchanged interface) ───────────────────────────────────


def extract_text_from_image(image_bytes: bytes) -> tuple[str, float]:
    """Extract text from an image. Returns (text, confidence 0-100)."""
    engine = settings.OCR_ENGINE

    if engine == "mock":
        return _mock_extract()
    if engine == "google_vision":
        return _google_vision_image(image_bytes)
    if engine == "easyocr":
        return _easyocr_image(image_bytes)
    # default: paddleocr
    return _paddle_image(image_bytes)


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[str, float]:
    """Extract text from a PDF. Returns (concatenated text, avg confidence)."""
    engine = settings.OCR_ENGINE

    if engine == "mock":
        return _mock_extract()
    if engine == "google_vision":
        return _google_vision_pdf(pdf_bytes)
    # PaddleOCR and EasyOCR: convert PDF to images, then OCR each page
    return _pdf_via_images(pdf_bytes, engine)


# ── PaddleOCR engine ──────────────────────────────────────────────────


def _get_paddle_ocr():
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR

        _paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang=settings.OCR_LANG,
            show_log=False,
            use_gpu=False,
        )
        logger.info("PaddleOCR engine initialized (lang=%s)", settings.OCR_LANG)
    return _paddle_ocr


def _paddle_image(image_bytes: bytes) -> tuple[str, float]:
    """Run PaddleOCR on image bytes."""
    ocr = _get_paddle_ocr()

    # PaddleOCR needs a file path or numpy array
    with NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        result = ocr.ocr(tmp_path, cls=True)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not result or not result[0]:
        return ("", 0.0)

    lines = []
    confidences = []
    for line in result[0]:
        text = line[1][0]
        conf = line[1][1]
        lines.append(text)
        confidences.append(conf)

    combined = "\n".join(lines)
    avg_conf = (sum(confidences) / len(confidences) * 100) if confidences else 0.0
    return (combined, round(avg_conf, 2))


# ── EasyOCR engine ────────────────────────────────────────────────────


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr

        langs = ["en"]
        if settings.OCR_LANG in ("hi", "devanagari"):
            langs.append("hi")
        _easyocr_reader = easyocr.Reader(langs, gpu=False)
        logger.info("EasyOCR reader initialized (langs=%s)", langs)
    return _easyocr_reader


def _easyocr_image(image_bytes: bytes) -> tuple[str, float]:
    """Run EasyOCR on image bytes."""
    reader = _get_easyocr_reader()
    results = reader.readtext(image_bytes)

    if not results:
        return ("", 0.0)

    lines = []
    confidences = []
    for bbox, text, conf in results:
        lines.append(text)
        confidences.append(conf)

    combined = "\n".join(lines)
    avg_conf = (sum(confidences) / len(confidences) * 100) if confidences else 0.0
    return (combined, round(avg_conf, 2))


# ── Google Cloud Vision engine ────────────────────────────────────────


def _google_vision_image(image_bytes: bytes) -> tuple[str, float]:
    """Run Google Cloud Vision document_text_detection on image bytes."""
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    if not response.full_text_annotation.text:
        return ("", 0.0)

    text = response.full_text_annotation.text
    confidences = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            confidences.append(block.confidence)
    avg_confidence = (sum(confidences) / len(confidences) * 100) if confidences else 50.0

    return (text, round(avg_confidence, 2))


def _google_vision_pdf(pdf_bytes: bytes) -> tuple[str, float]:
    """Convert PDF to images then run Google Vision on each page."""
    return _pdf_via_images(pdf_bytes, "google_vision")


# ── Shared PDF → image conversion ─────────────────────────────────────


def _pdf_via_images(pdf_bytes: bytes, engine: str) -> tuple[str, float]:
    """Generic PDF handler: convert pages to images, OCR each with given engine."""
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(pdf_bytes, dpi=300)
    all_text = []
    all_confidences = []

    # Pick the right image extractor
    if engine == "easyocr":
        img_fn = _easyocr_image
    elif engine == "google_vision":
        img_fn = _google_vision_image
    else:
        img_fn = _paddle_image

    for i, img in enumerate(images):
        buf = BytesIO()
        img.save(buf, format="PNG")
        page_bytes = buf.getvalue()

        text, confidence = img_fn(page_bytes)
        if text:
            all_text.append(f"--- Page {i + 1} ---\n{text}")
            all_confidences.append(confidence)

    combined_text = "\n\n".join(all_text)
    avg_confidence = (sum(all_confidences) / len(all_confidences)) if all_confidences else 0.0
    return (combined_text, round(avg_confidence, 2))


# ── Mock engine (dev/testing) ─────────────────────────────────────────


def _mock_extract() -> tuple[str, float]:
    """Return realistic sample Indian GST invoice text for local development."""
    sample_text = """TAX INVOICE
Original for Recipient

KUMAR ELECTRONICS PVT LTD
123, Industrial Area Phase-II, Chandigarh - 160002
GSTIN: 04AABCK1234M1Z5
State: 04-Chandigarh
Phone: 0172-2700000 | Email: info@kumarelectronics.com

Invoice No: KE/2024-25/0847
Invoice Date: 15/01/2025
Place of Supply: 04-Chandigarh

Bill To:
SHARMA TRADING CO.
45, Sector 22-B, Chandigarh - 160022
GSTIN: 04AADCS5678N1Z3
State: 04-Chandigarh

Sr. | Description of Goods      | HSN Code | Qty | Unit | Rate      | Amount
1   | LED Monitor 24 inch        | 85285900 | 10  | Nos  | 8,500.00  | 85,000.00
2   | Wireless Keyboard           | 84716060 | 20  | Nos  | 1,200.00  | 24,000.00
3   | USB-C Hub 7 Port            | 84733020 | 15  | Nos  | 2,500.00  | 37,500.00

                                        Taxable Value:    1,46,500.00
                                        CGST @ 9%:           13,185.00
                                        SGST @ 9%:           13,185.00
                                        Total Tax:           26,370.00
                                        Grand Total:      1,72,870.00

Amount in Words: Rupees One Lakh Seventy Two Thousand Eight Hundred and Seventy Only

Bank Details:
Bank Name: State Bank of India
A/C No: 30987654321
IFSC: SBIN0001234
Branch: Sector 17, Chandigarh

Terms & Conditions:
1. Payment due within 30 days
2. Interest @ 18% p.a. on delayed payments

Authorized Signatory
For KUMAR ELECTRONICS PVT LTD
"""
    return (sample_text, 87.5)
