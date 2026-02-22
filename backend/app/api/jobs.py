import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.models.job import Job
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get job status. Used by frontend to poll for processing completion."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Verify ownership through client
    result = await db.execute(
        select(Client).where(
            Client.id == job.client_id,
            Client.accountant_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    return job
