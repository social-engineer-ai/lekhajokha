import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.accountant import Accountant
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientResponse, ClientUpdate
from app.utils.constants import STATE_CODES

router = APIRouter(prefix="/clients", tags=["clients"])


def _extract_pan_from_gstin(gstin: str) -> str:
    """Extract PAN from GSTIN (characters 3-12)."""
    return gstin[2:12]


def _extract_state_code(gstin: str) -> str:
    """Extract state code from GSTIN (first 2 digits)."""
    return gstin[:2]


def _generate_ingest_email(business_name: str, client_id: uuid.UUID) -> str:
    """Generate unique ingest email for a client."""
    slug = business_name.lower().replace(" ", "-")[:20]
    short_id = str(client_id)[:8]
    return f"{slug}-{short_id}@{settings.INGEST_EMAIL_DOMAIN}"


@router.get("/", response_model=list[ClientResponse])
async def list_clients(
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client)
        .where(Client.accountant_id == current_user.id, Client.is_active == True)
        .order_by(Client.business_name)
    )
    return result.scalars().all()


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    req: ClientCreate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client_id = uuid.uuid4()
    pan = None
    state_code = None

    if req.gstin:
        pan = _extract_pan_from_gstin(req.gstin)
        state_code = _extract_state_code(req.gstin)

    ingest_email = _generate_ingest_email(req.business_name, client_id)

    client = Client(
        id=client_id,
        accountant_id=current_user.id,
        business_name=req.business_name,
        gstin=req.gstin,
        pan=pan,
        state_code=state_code,
        city=req.city,
        address=req.address,
        contact_name=req.contact_name,
        contact_phone=req.contact_phone,
        contact_email=req.contact_email,
        ingest_email=ingest_email,
        gst_username=req.gst_username,
        gst_filing_frequency=req.gst_filing_frequency,
    )
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.accountant_id == current_user.id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: uuid.UUID,
    req: ClientUpdate,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.accountant_id == current_user.id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = req.model_dump(exclude_unset=True)
    if "gstin" in update_data and update_data["gstin"]:
        update_data["pan"] = _extract_pan_from_gstin(update_data["gstin"])
        update_data["state_code"] = _extract_state_code(update_data["gstin"])

    for field, value in update_data.items():
        setattr(client, field, value)

    await db.flush()
    await db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: uuid.UUID,
    current_user: Accountant = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.accountant_id == current_user.id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.is_active = False
    await db.flush()
