import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.tally_config import TallyConfig
from app.models.job import Job
from app.schemas.tally import (
    TallyConfigResponse,
    TallyConfigUpdate,
    TallyConnectionTest,
    TallySyncRequest,
    TallyExportRequest,
)
from app.schemas.job import JobResponse
from app.services.tally_service import test_tally_connection, sync_to_tally, export_tally_xml

router = APIRouter(prefix="/tally", tags=["tally"])


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


@router.get("/config", response_model=TallyConfigResponse)
async def get_tally_config(
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current Tally config for authenticated accountant."""
    result = await db.execute(
        select(TallyConfig).where(TallyConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        # Create default config
        config = TallyConfig(
            id=uuid.uuid4(),
            accountant_id=current_user.id,
        )
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return config


@router.put("/config", response_model=TallyConfigResponse)
async def update_tally_config(
    data: TallyConfigUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update Tally host/port/company."""
    result = await db.execute(
        select(TallyConfig).where(TallyConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = TallyConfig(
            id=uuid.uuid4(),
            accountant_id=current_user.id,
        )
        db.add(config)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(config)
    return config


@router.post("/test-connection", response_model=TallyConnectionTest)
async def test_connection(
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test Tally connection using saved config."""
    result = await db.execute(
        select(TallyConfig).where(TallyConfig.accountant_id == current_user.id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return TallyConnectionTest(connected=False, error="Tally not configured. Save settings first.")

    test_result = await test_tally_connection(config.tally_host, config.tally_port)

    # Update connection status
    config.is_connected = test_result["connected"]
    if test_result["connected"] and test_result["company_name"]:
        config.company_name = test_result["company_name"]
    config.updated_at = datetime.now(timezone.utc)

    return TallyConnectionTest(**test_result)


@router.post("/clients/{client_id}/sync", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_tally_sync(
    client_id: uuid.UUID,
    data: TallySyncRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger sync to Tally as a background job."""
    client = await _verify_client_ownership(client_id, current_user, db)

    # Override scope if provided
    if data and data.scope:
        client.tally_sync_scope = data.scope

    job = Job(
        id=uuid.uuid4(),
        client_id=client_id,
        job_type="tally_sync",
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    background_tasks.add_task(sync_to_tally, client_id, job.id)
    return job


@router.post("/clients/{client_id}/export")
async def export_tally(
    client_id: uuid.UUID,
    data: TallyExportRequest,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate XML export for download (no Tally connection needed)."""
    client = await _verify_client_ownership(client_id, current_user, db)
    scope = data.scope or client.tally_sync_scope

    xml_content = await export_tally_xml(client_id, data.month, data.year, scope, db)

    filename = f"tally_export_{client.business_name}_{data.month:02d}_{data.year}.xml"
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
