import logging
from io import BytesIO

from app.config import settings

logger = logging.getLogger(__name__)


def extract_text_from_image(image_bytes: bytes) -> tuple[str, float]:
    """Extract text from an image using Google Cloud Vision or mock mode.
    Returns (text, confidence 0-100).
    """
    if not settings.GOOGLE_VISION_ENABLED:
        return _mock_extract()

    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    if not response.full_text_annotation.text:
        return ("", 0.0)

    text = response.full_text_annotation.text
    # Average confidence across pages
    confidences = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            confidences.append(block.confidence)
    avg_confidence = (sum(confidences) / len(confidences) * 100) if confidences else 50.0

    return (text, round(avg_confidence, 2))


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[str, float]:
    """Convert PDF pages to images and extract text from each.
    Returns (concatenated text, average confidence).
    """
    if not settings.GOOGLE_VISION_ENABLED:
        return _mock_extract()

    from pdf2image import convert_from_bytes

    images = convert_from_bytes(pdf_bytes, dpi=300)
    all_text = []
    all_confidences = []

    for i, img in enumerate(images):
        buf = BytesIO()
        img.save(buf, format="PNG")
        page_bytes = buf.getvalue()

        text, confidence = extract_text_from_image(page_bytes)
        if text:
            all_text.append(f"--- Page {i + 1} ---\n{text}")
            all_confidences.append(confidence)

    combined_text = "\n\n".join(all_text)
    avg_confidence = (sum(all_confidences) / len(all_confidences)) if all_confidences else 0.0

    return (combined_text, round(avg_confidence, 2))


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
