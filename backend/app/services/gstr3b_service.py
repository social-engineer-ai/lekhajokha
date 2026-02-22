"""GSTR-3B return generation from all invoices."""

import uuid
from datetime import date
from decimal import Decimal
from calendar import monthrange

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.invoice import Invoice


def _fmt_decimal(val: Decimal | None) -> float:
    if val is None:
        return 0.0
    return float(val)


def _get_state_code(gstin: str | None) -> str:
    if not gstin or len(gstin) < 2:
        return ""
    return gstin[:2]


async def generate_gstr3b(client_id: uuid.UUID, month: int, year: int, db: AsyncSession) -> dict:
    """Generate GSTR-3B summary from all invoices for a given period."""
    # Load client
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise ValueError("Client not found")

    # Date range
    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # Load all invoices for the period
    result = await db.execute(
        select(Invoice).options(selectinload(Invoice.line_items)).where(
            Invoice.client_id == client_id,
            Invoice.is_active == True,
            Invoice.processing_status == "completed",
            Invoice.invoice_date >= start_date,
            Invoice.invoice_date <= end_date,
        )
    )
    invoices = list(result.scalars().all())

    sales = [inv for inv in invoices if inv.invoice_type == "sales"]
    purchases = [inv for inv in invoices if inv.invoice_type == "purchase"]

    client_state = _get_state_code(client.gstin)

    # Section 3.1: Outward supplies
    outward_supplies = _compute_outward_supplies(sales, client_state)

    # Section 3.2: Inter-state supplies to unregistered persons
    inter_state_supplies = _compute_inter_state_unreg(sales, client_state)

    # Section 4: Eligible ITC
    eligible_itc = _compute_eligible_itc(purchases)

    # Section 6.1: Tax liability
    total_output_cgst = sum(_fmt_decimal(inv.cgst_amount) for inv in sales)
    total_output_sgst = sum(_fmt_decimal(inv.sgst_amount) for inv in sales)
    total_output_igst = sum(_fmt_decimal(inv.igst_amount) for inv in sales)
    total_output_tax = total_output_cgst + total_output_sgst + total_output_igst

    total_input_cgst = eligible_itc["cgst"]
    total_input_sgst = eligible_itc["sgst"]
    total_input_igst = eligible_itc["igst"]
    total_itc = total_input_cgst + total_input_sgst + total_input_igst

    net_cgst = max(0, total_output_cgst - total_input_cgst)
    net_sgst = max(0, total_output_sgst - total_input_sgst)
    net_igst = max(0, total_output_igst - total_input_igst)

    tax_liability = {
        "cgst": total_output_cgst,
        "sgst": total_output_sgst,
        "igst": total_output_igst,
        "cess": 0.0,
        "net_cgst": net_cgst,
        "net_sgst": net_sgst,
        "net_igst": net_igst,
    }

    period = f"{month:02d}{year}"

    return {
        "period": period,
        "gstin": client.gstin or "",
        "outward_supplies": outward_supplies,
        "inter_state_supplies": inter_state_supplies,
        "eligible_itc": eligible_itc,
        "tax_liability": tax_liability,
        "total_output_tax": total_output_tax,
        "total_itc": total_itc,
        "net_tax_payable": max(0, total_output_tax - total_itc),
    }


def _compute_outward_supplies(sales: list[Invoice], client_state: str) -> dict:
    """Section 3.1: Outward supplies and inward supplies liable to reverse charge."""
    taxable_value = 0.0
    igst = 0.0
    cgst = 0.0
    sgst = 0.0

    exempt_value = 0.0

    for inv in sales:
        taxable = _fmt_decimal(inv.taxable_amount)
        tax = _fmt_decimal(inv.total_tax)

        if tax > 0:
            taxable_value += taxable
            igst += _fmt_decimal(inv.igst_amount)
            cgst += _fmt_decimal(inv.cgst_amount)
            sgst += _fmt_decimal(inv.sgst_amount)
        else:
            exempt_value += taxable

    return {
        "taxable": {
            "txval": taxable_value,
            "igst": igst,
            "cgst": cgst,
            "sgst": sgst,
            "cess": 0.0,
        },
        "exempt": {
            "txval": exempt_value,
        },
        "nil_rated": {
            "txval": 0.0,
        },
        "non_gst": {
            "txval": 0.0,
        },
    }


def _compute_inter_state_unreg(sales: list[Invoice], client_state: str) -> dict:
    """Section 3.2: Inter-state supplies to unregistered persons."""
    # Invoices where buyer has no GSTIN and place of supply differs from client state
    inter_state_unreg = 0.0
    inter_state_igst = 0.0

    for inv in sales:
        if inv.buyer_gstin:
            continue
        pos_state = _get_state_code(inv.seller_gstin) if inv.seller_gstin else client_state
        inv_pos = inv.place_of_supply or ""
        # If IGST is charged, it's likely inter-state
        if _fmt_decimal(inv.igst_amount) > 0:
            inter_state_unreg += _fmt_decimal(inv.taxable_amount)
            inter_state_igst += _fmt_decimal(inv.igst_amount)

    return {
        "txval": inter_state_unreg,
        "igst": inter_state_igst,
    }


def _compute_eligible_itc(purchases: list[Invoice]) -> dict:
    """Section 4: Eligible ITC from purchase invoices."""
    igst = 0.0
    cgst = 0.0
    sgst = 0.0

    for inv in purchases:
        igst += _fmt_decimal(inv.igst_amount)
        cgst += _fmt_decimal(inv.cgst_amount)
        sgst += _fmt_decimal(inv.sgst_amount)

    return {
        "igst": igst,
        "cgst": cgst,
        "sgst": sgst,
        "cess": 0.0,
    }
