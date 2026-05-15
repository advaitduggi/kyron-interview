import os
import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid, server_default=text("gen_random_uuid()")
    )
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    dob: Mapped[date] = mapped_column(nullable=False)
    phone: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    sms_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("FALSE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=text("NOW()")
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session", back_populates="patient", lazy="selectin"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="patient", lazy="selectin"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid, server_default=text("gen_random_uuid()")
    )
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=True
    )
    # JSON works on both SQLite (as TEXT) and PostgreSQL (as json/jsonb via migration)
    conversation_state: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    appointment_state: Mapped[Any] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, server_default=text("NOW()")
    )

    patient: Mapped["Patient | None"] = relationship(
        "Patient", back_populates="sessions"
    )


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    specialty: Mapped[str] = mapped_column(Text, nullable=False)
    # Stored as a JSON array; use ARRAY(Text) in production via Alembic migration
    body_parts: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    availability: Mapped[list["Availability"]] = relationship(
        "Availability", back_populates="provider", lazy="selectin"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="provider", lazy="selectin"
    )


class Availability(Base):
    __tablename__ = "availability"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid, server_default=text("gen_random_uuid()")
    )
    provider_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("providers.id"), nullable=True
    )
    slot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("FALSE"))

    provider: Mapped["Provider | None"] = relationship(
        "Provider", back_populates="availability"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid, server_default=text("gen_random_uuid()")
    )
    patient_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=True
    )
    provider_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("providers.id"), nullable=True
    )
    slot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="confirmed", server_default=text("'confirmed'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=text("NOW()")
    )

    patient: Mapped["Patient | None"] = relationship(
        "Patient", back_populates="appointments"
    )
    provider: Mapped["Provider | None"] = relationship(
        "Provider", back_populates="appointments"
    )


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

def _make_engine():
    url = os.environ["DATABASE_URL"]
    return create_async_engine(url, echo=False, pool_pre_ping=True)


engine = _make_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
