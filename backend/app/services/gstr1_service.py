"""GSTR-1 return generation from sales invoices."""

import uuid
from datetime import date
from decimal import Decimal
from calendar import monthrange
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.invoice import Invoice

# Indian state codes for GSTIN → state mapping
STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
    "29": "Karnataka", "30": "Goa", "32": "Kerala",
    "33": "Tamil Nadu", "34": "Puducherry", "36": "Telangana",
    "37": "Andhra Pradesh",
}


def _get_state_from_gstin(gstin: str | None) -> str:
    if not gstin or len(gstin) < 2:
        return ""
    return STATE_CODES.get(gstin[:2], "")


def _fmt_decimal(val: Decimal | None) -> float:
    if val is None:
        return 0.0
    return float(val)


async def generate_gstr1(client_id: uuid.UUID, month: int, year: int, db: AsyncSession) -> dict:
    """Generate GSTR-1 data from sales invoices for a given period."""
    # Load client
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise ValueError("Client not found")

    # Date range
    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # Load sales invoices for the period
    result = await db.execute(
        select(Invoice).options(selectinload(Invoice.line_items)).where(
            Invoice.client_id == client_id,
            Invoice.is_active == True,
            Invoice.processing_status == "completed",
            Invoice.invoice_type == "sales",
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
        )
    )
    invoices = list(result.scalars().all())

    client_state = _get_state_from_gstin(client.gstin)

    b2b = _build_b2b_section(invoices)
    b2cs = _build_b2cs_section(invoices, client_state)
    hsn = _build_hsn_section(invoices)

    total_taxable = sum(_fmt_decimal(inv.taxable_amount) for inv in invoices)
    total_tax = sum(_fmt_decimal(inv.total_tax) for inv in invoices)

    period = f"{month:02d}{year}"

    return {
        "period": period,
        "gstin": client.gstin or "",
        "b2b": b2b,
        "b2cs": b2cs,
        "hsn": hsn,
        "total_invoices": len(invoices),
        "total_taxable": total_taxable,
        "total_tax": total_tax,
    }


def _build_b2b_section(invoices: list[Invoice]) -> list[dict]:
    """Group by buyer GSTIN, then list invoices with tax breakdown."""
    # Only invoices where buyer has GSTIN
    b2b_invoices = [inv for inv in invoices if inv.buyer_gstin]

    # Group by buyer GSTIN
    grouped: dict[str, list[Invoice]] = defaultdict(list)
    for inv in b2b_invoices:
        grouped[inv.buyer_gstin].append(inv)

    result = []
    for gstin, inv_list in grouped.items():
        buyer_entry = {
            "ctin": gstin,
            "inv": []
        }
        for inv in inv_list:
            inv_entry = {
                "inum": inv.invoice_number or "",
                "idt": inv.invoice_date.strftime("%d-%m-%Y") if inv.invoice_date else "",
                "val": _fmt_decimal(inv.total_amount),
                "pos": inv.place_of_supply or _get_state_from_gstin(gstin)[:2] if gstin else "",
                "rchrg": "N",
                "inv_typ": "R",
                "itms": [],
            }
            # Build item-wise tax details
            rates_seen: dict[float, dict] = {}
            for item in inv.line_items:
                rate = float(item.gst_rate) if item.gst_rate else 0.0
                if rate not in rates_seen:
                    rates_seen[rate] = {
                        "rt": rate,
                        "txval": 0.0,
                        "camt": 0.0,
                        "samt": 0.0,
                        "iamt": 0.0,
                    }
                rates_seen[rate]["txval"] += _fmt_decimal(item.amount)
                rates_seen[rate]["camt"] += _fmt_decimal(item.cgst_amount)
                rates_seen[rate]["samt"] += _fmt_decimal(item.sgst_amount)
                rates_seen[rate]["iamt"] += _fmt_decimal(item.igst_amount)

            if not rates_seen:
                # Use invoice-level amounts if no line items
                rate = 0.0
                if inv.taxable_amount and inv.taxable_amount > 0 and inv.total_tax:
                    rate = float(inv.total_tax / inv.taxable_amount * 100)
                    rate = round(rate)
                rates_seen[rate] = {
                    "rt": rate,
                    "txval": _fmt_decimal(inv.taxable_amount),
                    "camt": _fmt_decimal(inv.cgst_amount),
                    "samt": _fmt_decimal(inv.sgst_amount),
                    "iamt": _fmt_decimal(inv.igst_amount),
                }

            for idx, (rate, details) in enumerate(rates_seen.items(), 1):
                inv_entry["itms"].append({
                    "num": idx,
                    "itm_det": details,
                })

            buyer_entry["inv"].append(inv_entry)
        result.append(buyer_entry)

    return result


def _build_b2cs_section(invoices: list[Invoice], client_state: str) -> list[dict]:
    """Aggregate B2C small invoices by rate + place of supply."""
    # B2CS: buyer has no GSTIN
    b2cs_invoices = [inv for inv in invoices if not inv.buyer_gstin]

    # Aggregate by (rate, place_of_supply, supply_type)
    aggregated: dict[tuple, dict] = {}

    for inv in b2cs_invoices:
        pos = inv.place_of_supply or client_state
        # Determine if inter-state
        inv_state = _get_state_from_gstin(inv.seller_gstin) if inv.seller_gstin else client_state
        supply_type = "INTRA" if pos == inv_state or pos == client_state else "INTER"

        # Determine rate
        rate = 0.0
        if inv.taxable_amount and inv.taxable_amount > 0 and inv.total_tax:
            rate = float(inv.total_tax / inv.taxable_amount * 100)
            rate = round(rate)

        key = (rate, pos, supply_type)
        if key not in aggregated:
            aggregated[key] = {
                "rt": rate,
                "pos": pos[:2] if len(pos) >= 2 else pos,
                "sply_ty": supply_type,
                "txval": 0.0,
                "camt": 0.0,
                "samt": 0.0,
                "iamt": 0.0,
            }

        aggregated[key]["txval"] += _fmt_decimal(inv.taxable_amount)
        aggregated[key]["camt"] += _fmt_decimal(inv.cgst_amount)
        aggregated[key]["samt"] += _fmt_decimal(inv.sgst_amount)
        aggregated[key]["iamt"] += _fmt_decimal(inv.igst_amount)

    return list(aggregated.values())


def _build_hsn_section(invoices: list[Invoice]) -> list[dict]:
    """Aggregate by HSN code across all invoices."""
    hsn_agg: dict[str, dict] = {}

    for inv in invoices:
        for item in inv.line_items:
            hsn = item.hsn_sac_code or "0000"
            if hsn not in hsn_agg:
                hsn_agg[hsn] = {
                    "hsn_sc": hsn,
                    "desc": item.description[:30] if item.description else "",
                    "qty": 0.0,
                    "txval": 0.0,
                    "camt": 0.0,
                    "samt": 0.0,
                    "iamt": 0.0,
                    "rt": float(item.gst_rate) if item.gst_rate else 0.0,
                }
            hsn_agg[hsn]["qty"] += float(item.quantity) if item.quantity else 0.0
            hsn_agg[hsn]["txval"] += _fmt_decimal(item.amount)
            hsn_agg[hsn]["camt"] += _fmt_decimal(item.cgst_amount)
            hsn_agg[hsn]["samt"] += _fmt_decimal(item.sgst_amount)
            hsn_agg[hsn]["iamt"] += _fmt_decimal(item.igst_amount)

    return list(hsn_agg.values())
