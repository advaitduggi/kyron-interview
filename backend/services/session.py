import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Session


async def load_session(session_id: str, db: AsyncSession) -> Session | None:
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def save_session(
    session_id: str,
    messages: list,
    appointment_state: dict,
    db: AsyncSession,
) -> Session:
    session = await load_session(session_id, db)

    safe_state = json.loads(json.dumps(messages, default=str))

    if session is not None:
        session.conversation_state = safe_state
        session.appointment_state = appointment_state
        session.updated_at = datetime.now(timezone.utc)
    else:
        session = Session(
            id=session_id,
            conversation_state=safe_state,
            appointment_state=appointment_state,
        )
        db.add(session)

    await db.commit()
    await db.refresh(session)
    return session


async def create_session(patient_id: str, db: AsyncSession) -> Session:
    session = Session(
        patient_id=patient_id,
        conversation_state=[],
        appointment_state={},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session
