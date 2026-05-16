import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Availability, Provider, get_db

router = APIRouter(prefix="/admin")


class ToggleBody(BaseModel):
    is_booked: bool


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

_CONFIRMATION_PREFIX = "KM-"


def _confirmation_number(appointment_id: str) -> str:
    return _CONFIRMATION_PREFIX + appointment_id.replace("-", "")[:8].upper()


@router.get("/providers", dependencies=[Depends(require_admin)])
async def list_providers(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Provider))
    providers = result.scalars().all()

    # Provider.availability and Provider.appointments are lazy="selectin" — already loaded.
    # Build a slot_time -> appointment map for each provider to annotate booked slots.
    provider_list = []
    for p in providers:
        appt_by_slot: dict = {}
        for appt in (p.appointments or []):
            if appt.status == "confirmed" and appt.patient:
                appt_by_slot[appt.slot_time] = appt

        slots = []
        for slot in sorted(p.availability, key=lambda s: s.slot_time):
            appt = appt_by_slot.get(slot.slot_time) if slot.is_booked else None
            entry: dict = {
                "id": slot.id,
                "slot_time": slot.slot_time.isoformat(),
                "is_booked": slot.is_booked,
                "appointment_id": _confirmation_number(appt.id) if appt else None,
                "patient_name": f"{appt.patient.first_name} {appt.patient.last_name}" if appt else None,
                "patient_phone": appt.patient.phone if appt else None,
                "reason": appt.reason if appt else None,
            }
            slots.append(entry)

        provider_list.append({
            "id": p.id,
            "name": p.name,
            "specialty": p.specialty,
            "body_parts": p.body_parts,
            "bio": p.bio,
            "availability": slots,
        })

    return {"providers": provider_list}


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
    body: ToggleBody,
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
