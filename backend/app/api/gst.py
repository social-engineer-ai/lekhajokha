import json
import uuid
from datetime import date
from decimal import Decimal
from calendar import monthrange

import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.invoice import Invoice
from app.schemas.gst import GSTReturnRequest, GSTR1Response, GSTR3BResponse, GSTSummary
from app.services.gstr1_service import generate_gstr1
from app.services.gstr3b_service import generate_gstr3b
from app.services.notification_service import notify

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clients/{client_id}/gst", tags=["gst"])


async def _verify_client_ownership(
    client_id: uuid.UUID, current_user: Accountant, db: AsyncSession
) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.accountant_id == current_user.id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/summary", response_model=GSTSummary)
async def get_gst_summary(
    client_id: uuid.UUID,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2100),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Monthly GST summary (tax liability overview)."""
    await _verify_client_ownership(client_id, current_user, db)

    _, last_day = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    base_filter = [
        Invoice.client_id == client_id,
        Invoice.is_active == True,
        Invoice.processing_status == "completed",
        Invoice.invoice_date >= start_date,
        Invoice.invoice_date <= end_date,
    ]

    # Sales stats
    sales_result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Invoice.total_tax), 0),
        ).where(*base_filter, Invoice.invoice_type == "sales")
    )
    sales_row = sales_result.one()
    total_sales = sales_row[0]
    output_tax = float(sales_row[1])

    # Purchase stats
    purchase_result = await db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(Invoice.total_tax), 0),
        ).where(*base_filter, Invoice.invoice_type == "purchase")
    )
    purchase_row = purchase_result.one()
    total_purchases = purchase_row[0]
    input_tax = float(purchase_row[1])

    period = f"{month:02d}{year}"

    return GSTSummary(
        period=period,
        total_sales_invoices=total_sales,
        total_purchase_invoices=total_purchases,
        total_output_tax=output_tax,
        total_input_tax=input_tax,
        net_tax_liability=max(0, output_tax - input_tax),
    )


@router.post("/gstr1", response_model=GSTR1Response)
async def get_gstr1(
    client_id: uuid.UUID,
    data: GSTReturnRequest,
    background_tasks: BackgroundTasks,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate GSTR-1 from sales invoices."""
    await _verify_client_ownership(client_id, current_user, db)
    result = await generate_gstr1(client_id, data.month, data.year, db)

    # Fire notification in background
    period = f"{data.month:02d}/{data.year}"
    background_tasks.add_task(
        notify, client_id, current_user.id, "gst_return_ready",
        {"return_type": "GSTR-1", "period": period},
    )

    return GSTR1Response(**result)


@router.post("/gstr1/export")
async def export_gstr1(
    client_id: uuid.UUID,
    data: GSTReturnRequest,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download GSTR-1 as JSON file (GST portal format)."""
    client = await _verify_client_ownership(client_id, current_user, db)
    result = await generate_gstr1(client_id, data.month, data.year, db)

    # Format for GST portal
    portal_json = {
        "gstin": result["gstin"],
        "fp": result["period"],
        "b2b": result["b2b"],
        "b2cs": result["b2cs"],
        "hsn": {"data": result["hsn"]},
    }

    content = json.dumps(portal_json, indent=2, default=str)
    filename = f"GSTR1_{result['gstin']}_{result['period']}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/gstr3b", response_model=GSTR3BResponse)
async def get_gstr3b(
    client_id: uuid.UUID,
    data: GSTReturnRequest,
    background_tasks: BackgroundTasks,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate GSTR-3B summary."""
    await _verify_client_ownership(client_id, current_user, db)
    result = await generate_gstr3b(client_id, data.month, data.year, db)

    # Fire notification in background
    period = f"{data.month:02d}/{data.year}"
    background_tasks.add_task(
        notify, client_id, current_user.id, "gst_return_ready",
        {"return_type": "GSTR-3B", "period": period},
    )

    return GSTR3BResponse(**result)


@router.post("/gstr3b/export")
async def export_gstr3b(
    client_id: uuid.UUID,
    data: GSTReturnRequest,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download GSTR-3B as JSON file."""
    client = await _verify_client_ownership(client_id, current_user, db)
    result = await generate_gstr3b(client_id, data.month, data.year, db)

    portal_json = {
        "gstin": result["gstin"],
        "ret_period": result["period"],
        "sup_details": result["outward_supplies"],
        "inter_sup": result["inter_state_supplies"],
        "itc_elg": result["eligible_itc"],
        "tax_pmt": result["tax_liability"],
    }

    content = json.dumps(portal_json, indent=2, default=str)
    filename = f"GSTR3B_{result['gstin']}_{result['period']}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
