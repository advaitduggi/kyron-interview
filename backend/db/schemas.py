from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------------------------------------------------------------------------
# Intake
# ---------------------------------------------------------------------------

class IntakeRequest(BaseModel):
    first_name: str
    last_name: str
    dob: date
    phone: str
    email: EmailStr
    sms_opt_in: bool = False


class IntakeResponse(BaseModel):
    patient_id: str
    session_id: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str | None = None
    patient_id: str | None = None
    message: str


# SSE event shapes — used by the streaming endpoint for documentation / typing

class TextDeltaEvent(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class ToolCallEvent(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool: str
    args: dict[str, Any]


class ToolResultEvent(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    result: Any


class EndEvent(BaseModel):
    type: Literal["end"] = "end"
    session_id: str


# Non-streaming fallback (used in tests / simple clients)
class ChatResponse(BaseModel):
    session_id: str
    message: str


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    specialty: str
    body_parts: list[str]
    bio: str | None = None


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

class AvailabilitySlot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    provider_name: str
    specialty: str
    slot_time: datetime
    is_booked: bool


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str | None
    provider_id: str | None
    slot_time: datetime
    reason: str | None = None
    status: str
    created_at: datetime

    # Denormalised convenience fields (populated by the router, not the ORM)
    provider_name: str | None = None
    confirmation_number: str | None = None


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class AvailabilityToggle(BaseModel):
    """PATCH /admin/providers/{id}/availability — flip a single slot."""
    slot_id: str
    is_booked: bool


class BulkAvailabilityRequest(BaseModel):
    """Add many open slots at once."""
    provider_id: str
    slots: list[datetime]


# ---------------------------------------------------------------------------
# Session resume
# ---------------------------------------------------------------------------

class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str | None
    conversation_state: list[Any]
    appointment_state: dict[str, Any]
    updated_at: datetime
