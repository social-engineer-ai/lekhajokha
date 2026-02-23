"""Cashfree UPI VPA verification service. Mock mode by default for dev."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Mock VPA database for development
MOCK_VPA_DB = {
    "merchant@upi": {"registered_name": "Merchant Enterprises", "is_valid": True},
    "shop@ybl": {"registered_name": "Shop India Pvt Ltd", "is_valid": True},
    "vendor@paytm": {"registered_name": "Vendor Solutions", "is_valid": True},
    "invalid@upi": {"registered_name": None, "is_valid": False},
}


async def verify_vpa(vpa: str) -> dict:
    """Verify a UPI VPA and return the registered name.

    Returns:
        {"vpa": str, "is_valid": bool, "registered_name": str|None, "source": "cashfree"|"cashfree_mock"}
    """
    vpa = vpa.strip().lower()

    if settings.CASHFREE_MOCK:
        return _mock_verify(vpa)

    return await _cashfree_verify(vpa)


def _mock_verify(vpa: str) -> dict:
    """Mock verification for development."""
    mock_data = MOCK_VPA_DB.get(vpa)
    if mock_data:
        return {
            "vpa": vpa,
            "is_valid": mock_data["is_valid"],
            "registered_name": mock_data["registered_name"],
            "source": "cashfree_mock",
        }
    # For unknown VPAs in mock mode, return a generated name
    local_part = vpa.split("@")[0] if "@" in vpa else vpa
    return {
        "vpa": vpa,
        "is_valid": True,
        "registered_name": local_part.replace(".", " ").replace("_", " ").title(),
        "source": "cashfree_mock",
    }


async def _cashfree_verify(vpa: str) -> dict:
    """Real Cashfree API call for VPA verification."""
    url = f"{settings.CASHFREE_BASE_URL}/payout/v1/validation/upiDetails"
    headers = {
        "X-Client-Id": settings.CASHFREE_APP_ID,
        "X-Client-Secret": settings.CASHFREE_SECRET_KEY,
        "Content-Type": "application/json",
    }
    payload = {"upi": vpa}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            is_valid = data.get("status") == "SUCCESS" and data.get("data", {}).get("accountExists") == "YES"
            registered_name = data.get("data", {}).get("nameAtBank")

            return {
                "vpa": vpa,
                "is_valid": is_valid,
                "registered_name": registered_name if is_valid else None,
                "source": "cashfree",
            }

    except httpx.HTTPStatusError as e:
        logger.error(f"Cashfree API error for {vpa}: {e.response.status_code} {e.response.text[:200]}")
        return {"vpa": vpa, "is_valid": False, "registered_name": None, "source": "cashfree"}
    except Exception as e:
        logger.exception(f"Cashfree API call failed for {vpa}: {e}")
        raise
