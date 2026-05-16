import os
from datetime import datetime  # noqa: F401 — used by _naive type hint

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Appointment, Availability, Patient, Provider, get_db

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


def _naive(dt) -> "datetime":
    """Strip timezone info so SQLite naive and aware datetimes compare equal."""
    return dt.replace(tzinfo=None) if dt else dt


@router.get("/providers", dependencies=[Depends(require_admin)])
async def list_providers(db: AsyncSession = Depends(get_db)) -> dict:
    providers_result = await db.execute(select(Provider))
    providers = providers_result.scalars().all()

    # Fetch all confirmed appointments with their patients in one query.
    appts_result = await db.execute(
        select(Appointment, Patient)
        .join(Patient, Appointment.patient_id == Patient.id)
        .where(Appointment.status == "confirmed")
    )
    # Key: (provider_id, naive slot_time) -> (Appointment, Patient)
    appt_map: dict[tuple, tuple] = {}
    for appt, patient in appts_result.all():
        appt_map[(_naive(appt.slot_time), appt.provider_id)] = (appt, patient)

    provider_list = []
    for p in providers:
        slots = []
        for slot in sorted(p.availability, key=lambda s: s.slot_time):
            pair = appt_map.get((_naive(slot.slot_time), p.id)) if slot.is_booked else None
            appt, patient = pair if pair else (None, None)
            entry: dict = {
                "id": slot.id,
                "slot_time": slot.slot_time.isoformat(),
                "is_booked": slot.is_booked,
                "appointment_id": _confirmation_number(appt.id) if appt else None,
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
                "patient_phone": patient.phone if patient else None,
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
