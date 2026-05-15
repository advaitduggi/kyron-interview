import logging
import traceback
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Appointment, Availability, Provider

logger = logging.getLogger(__name__)

TOOL_DEFINITION = {
    "name": "book_appointment",
    "description": (
        "Book an appointment for a patient. "
        "Only call this after confirming all details with the patient. "
        "Returns a confirmation number on success, or next available slots if the slot was just taken."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "UUID of the patient (from intake).",
            },
            "slot_id": {
                "type": "string",
                "description": "UUID of the availability slot the patient selected.",
            },
            "reason": {
                "type": "string",
                "description": "Brief description of the reason for the visit.",
            },
        },
        "required": ["patient_id", "slot_id", "reason"],
    },
}

_CONFIRMATION_PREFIX = "KM-"


def _confirmation_number(appointment_id: str) -> str:
    return _CONFIRMATION_PREFIX + appointment_id.replace("-", "")[:8].upper()


async def _next_available(db: AsyncSession, provider_id: str, after: datetime) -> list[dict]:
    """Return up to 3 open slots for the provider within 7 days of `after`."""
    window_end = after + timedelta(days=7)
    stmt = (
        select(Availability)
        .where(
            Availability.provider_id == provider_id,
            Availability.is_booked.is_(False),
            Availability.slot_time > after,
            Availability.slot_time <= window_end,
        )
        .order_by(Availability.slot_time)
        .limit(3)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [{"slot_id": r.id, "slot_time": r.slot_time.isoformat()} for r in rows]


async def execute(args: dict, db: AsyncSession) -> dict:
    logger.info("book_appointment args: %s", args)
    try:
        patient_id: str = args["patient_id"]
        slot_id: str = args["slot_id"]
        reason: str = args["reason"]

        # Use the caller's existing session transaction — do NOT call db.begin()
        # here because the chat router's get_db session already has an open
        # transaction (autobegin fired on the first SELECT in load_session).
        # with_for_update() is also omitted: SQLite doesn't support it, and
        # the single-writer session lock is sufficient for the dev environment.
        slot_stmt = select(Availability).where(Availability.id == slot_id)
        slot = (await db.execute(slot_stmt)).scalar_one_or_none()

        if slot is None:
            return {"error": "slot_not_found", "message": "The requested slot does not exist."}

        if slot.is_booked:
            next_slots = await _next_available(db, slot.provider_id, slot.slot_time)
            return {
                "error": "slot_taken",
                "message": "That slot was just booked by someone else.",
                "next_available": next_slots,
            }

        # Mark slot as booked and create the appointment.
        slot.is_booked = True

        appointment = Appointment(
            patient_id=patient_id,
            provider_id=slot.provider_id,
            slot_time=slot.slot_time,
            reason=reason,
            status="confirmed",
        )
        db.add(appointment)
        await db.flush()  # materialise appointment.id; commit happens in save_session

        provider_stmt = select(Provider).where(Provider.id == slot.provider_id)
        provider = (await db.execute(provider_stmt)).scalar_one_or_none()
        provider_name = provider.name if provider else "Unknown Provider"

        confirmation = _confirmation_number(appointment.id)

        return {
            "appointment_id": appointment.id,
            "provider_name": provider_name,
            "slot_time": slot.slot_time.isoformat(),
            "confirmation_number": confirmation,
        }
    except Exception as e:
        logger.error("book_appointment failed: %s", traceback.format_exc())
        return {"error": str(e)}
