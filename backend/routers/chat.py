import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Patient, get_db
from db.schemas import ChatRequest, ChatResponse, IntakeRequest, IntakeResponse
from services import ai, notifications
from services.session import create_session, load_session, save_session

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _find_booking_result(messages: list) -> dict | None:
    """Scan messages in reverse for the most recent book_appointment tool result."""
    for msg in reversed(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            result = block.get("content")
            if isinstance(result, dict) and "appointment_id" in result:
                return result
    return None


# ---------------------------------------------------------------------------
# POST /intake
# ---------------------------------------------------------------------------

@router.post("/intake", response_model=IntakeResponse)
async def intake(body: IntakeRequest, db: AsyncSession = Depends(get_db)) -> IntakeResponse:
    patient = Patient(
        first_name=body.first_name,
        last_name=body.last_name,
        dob=body.dob,
        phone=body.phone,
        email=body.email,
        sms_opt_in=body.sms_opt_in,
    )
    db.add(patient)
    await db.flush()  # generate patient.id before create_session references it

    session = await create_session(patient_id=patient.id, db=db)
    await db.commit()

    return IntakeResponse(patient_id=patient.id, session_id=session.id)


# ---------------------------------------------------------------------------
# POST /chat
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    body: ChatRequest, db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    # Load session
    if not body.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = await load_session(body.session_id, db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Reconstruct mutable message list from persisted state
    messages: list = list(session.conversation_state or [])
    appointment_state: dict = dict(session.appointment_state or {})

    # On the first turn of a session, inject the patient info that was already
    # collected by the intake form so the AI doesn't ask for it again.
    if not messages and body.patient_id:
        result = await db.execute(select(Patient).where(Patient.id == body.patient_id))
        known_patient = result.scalar_one_or_none()
        if known_patient:
            messages.append({
                "role": "user",
                "content": (
                    f"[Patient info on file — Name: {known_patient.first_name} {known_patient.last_name}, "
                    f"DOB: {known_patient.dob}, Phone: {known_patient.phone}, "
                    f"Email: {known_patient.email}]"
                ),
            })
            messages.append({
                "role": "assistant",
                "content": (
                    f"Thank you, {known_patient.first_name}. I have your information on file. "
                    "How can I help you today?"
                ),
            })

    # Append the new user turn
    messages.append({"role": "user", "content": body.message})

    # Run the agentic loop (mutates messages in-place)
    reply = await ai.run_turn(messages, db)

    # Persist updated session
    await save_session(
        session_id=body.session_id,
        messages=messages,
        appointment_state=appointment_state,
        db=db,
    )

    # Fire notifications if this turn completed a booking
    booking = _find_booking_result(messages)
    if booking:
        patient_name = "Patient"
        patient_email: str | None = None
        patient_phone: str | None = None
        sms_opt_in = False

        if body.patient_id:
            result = await db.execute(select(Patient).where(Patient.id == body.patient_id))
            patient = result.scalar_one_or_none()
            if patient:
                patient_name = f"{patient.first_name} {patient.last_name}"
                patient_email = patient.email
                patient_phone = patient.phone
                sms_opt_in = patient.sms_opt_in

        if patient_email:
            asyncio.create_task(
                notifications.send_confirmation_email(
                    patient_email=patient_email,
                    patient_name=patient_name,
                    provider_name=booking.get("provider_name", "your doctor"),
                    slot_time=booking.get("slot_time", ""),
                    appointment_id=booking["appointment_id"],
                )
            )

        if sms_opt_in and patient_phone:
            asyncio.create_task(
                notifications.send_confirmation_sms(
                    patient_phone=patient_phone,
                    provider_name=booking.get("provider_name", "your doctor"),
                    slot_time=booking.get("slot_time", ""),
                )
            )

    # Stream response
    async def event_stream():
        yield _sse({"type": "text_delta", "text": reply})
        yield _sse({"type": "end", "session_id": body.session_id})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
