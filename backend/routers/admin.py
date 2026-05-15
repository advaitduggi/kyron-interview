import os

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Availability, Provider, get_db
from db.schemas import AvailabilityToggle

router = APIRouter(prefix="/admin")


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def require_admin(x_admin_secret: str = Header(default="")) -> None:
    expected = os.environ.get("ADMIN_SECRET", "")
    if not expected or x_admin_secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# GET /admin/providers
# ---------------------------------------------------------------------------

@router.get("/providers", dependencies=[Depends(require_admin)])
async def list_providers(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Provider))
    providers = result.scalars().all()

    # Provider.availability is lazy="selectin" so it's already loaded
    return {
        "providers": [
            {
                "id": p.id,
                "name": p.name,
                "specialty": p.specialty,
                "body_parts": p.body_parts,
                "bio": p.bio,
                "availability": [
                    {
                        "id": slot.id,
                        "slot_time": slot.slot_time.isoformat(),
                        "is_booked": slot.is_booked,
                    }
                    for slot in sorted(p.availability, key=lambda s: s.slot_time)
                ],
            }
            for p in providers
        ]
    }


# ---------------------------------------------------------------------------
# PATCH /admin/providers/{provider_id}/availability/{slot_id}
# ---------------------------------------------------------------------------

@router.patch(
    "/providers/{provider_id}/availability/{slot_id}",
    dependencies=[Depends(require_admin)],
)
async def toggle_slot(
    provider_id: str,
    slot_id: str,
    body: AvailabilityToggle,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Availability).where(
            Availability.id == slot_id,
            Availability.provider_id == provider_id,
        )
    )
    slot = result.scalar_one_or_none()

    if slot is None:
        raise HTTPException(status_code=404, detail="Slot not found")

    slot.is_booked = body.is_booked
    await db.commit()
    await db.refresh(slot)

    return {
        "id": slot.id,
        "provider_id": slot.provider_id,
        "slot_time": slot.slot_time.isoformat(),
        "is_booked": slot.is_booked,
    }
