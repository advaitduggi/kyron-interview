import os
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Patient, get_db
from services.ai import _system_prompt
from services.session import load_session

router = APIRouter()

VAPI_CALL_URL = "https://api.vapi.ai/call/phone"


def normalize_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    return f"+{digits}"


class CallRequest(BaseModel):
    session_id: str
    patient_id: str


def _format_history(conversation_state: list) -> str:
    lines = []
    for msg in conversation_state:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_result":
                        parts.append(f"[tool result: {block.get('content', '')}]")
            content = " ".join(p for p in parts if p)
        if not content or not role:
            continue
        label = "Patient" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


@router.post("/call")
async def initiate_call(body: CallRequest, db: AsyncSession = Depends(get_db)) -> dict:
    api_key = os.environ.get("VAPI_API_KEY", "")
    phone_number_id = os.environ.get("VAPI_PHONE_NUMBER_ID", "")

    if not api_key or not phone_number_id:
        raise HTTPException(status_code=503, detail="Voice call service not configured")

    session = await load_session(body.session_id, db)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(select(Patient).where(Patient.id == body.patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not patient.phone:
        raise HTTPException(status_code=422, detail="No phone number on file for this patient")

    history = _format_history(session.conversation_state or [])
    system_prompt = _system_prompt()
    if history:
        system_prompt += f"\n\nCurrent conversation history:\n{history}"

    payload = {
        "phoneNumberId": phone_number_id,
        "customer": {"number": normalize_phone(patient.phone)},
        "assistant": {
            "model": {
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "systemPrompt": system_prompt,
            },
            "firstMessage": (
                f"Hi {patient.first_name}, I'm continuing your appointment booking. "
                "I have the full context of your chat — shall we pick up where we left off?"
            ),
        },
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            VAPI_CALL_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Vapi error {resp.status_code}: {resp.text[:200]}",
        )

    data = resp.json()
    return {"call_id": data.get("id", ""), "status": "initiated"}
