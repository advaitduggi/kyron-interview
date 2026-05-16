"""
Seed script — run from the backend/ directory:
    python db/seed.py
"""
import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone

# Allow `from db.models import ...` when run as a script from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from sqlalchemy import select

from db.models import AsyncSessionLocal, Availability, Base, Provider, engine

# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

PROVIDERS = [
    {
        "name": "Dr. Sarah Chen",
        "specialty": "Orthopedics",
        "body_parts": ["knee", "hip", "shoulder", "back", "spine", "joint", "bone", "fracture"],
        "bio": "Board-certified orthopedic surgeon with 15 years of experience.",
    },
    {
        "name": "Dr. Marcus Webb",
        "specialty": "Cardiology",
        "body_parts": ["heart", "chest", "cardiac", "palpitations", "blood pressure", "cardiovascular"],
        "bio": "Interventional cardiologist specializing in preventive care.",
    },
    {
        "name": "Dr. Priya Nair",
        "specialty": "Dermatology",
        "body_parts": ["skin", "rash", "mole", "acne", "eczema", "psoriasis", "hair", "nail"],
        "bio": "Dermatologist focused on medical and cosmetic skin conditions.",
    },
    {
        "name": "Dr. James Okafor",
        "specialty": "Neurology",
        "body_parts": ["head", "brain", "headache", "migraine", "nerve", "numbness", "seizure", "memory"],
        "bio": "Neurologist with expertise in headache disorders and epilepsy.",
    },
]

SLOT_HOURS = [13, 14, 15, 18, 19, 20]  # 9am–11am, 2pm–4pm EDT (UTC-4)
SEED_DAYS = 45


def _generate_slots(provider_id: str, start: date) -> list[Availability]:
    slots = []
    current = start
    days_added = 0
    while days_added < SEED_DAYS:
        if current.weekday() not in (5, 6):  # skip Saturday=5, Sunday=6
            for hour in SLOT_HOURS:
                slot_time = datetime(
                    current.year, current.month, current.day,
                    hour, 0, 0, tzinfo=timezone.utc,
                )
                slots.append(Availability(provider_id=provider_id, slot_time=slot_time))
            days_added += 1
        current += timedelta(days=1)
    return slots


async def main() -> None:
    # 1. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created (or already exist).")

    # 2. Check idempotency
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Provider).limit(1))
        if result.scalar_one_or_none() is not None:
            print("Providers table already has rows — skipping seed.")
            return

        # 3. Seed providers
        providers = [Provider(**p) for p in PROVIDERS]
        session.add_all(providers)
        await session.flush()  # populate server-generated IDs

        # 4. Generate availability slots
        tomorrow = date.today() + timedelta(days=1)
        all_slots: list[Availability] = []
        for provider in providers:
            all_slots.extend(_generate_slots(provider.id, tomorrow))

        session.add_all(all_slots)
        await session.commit()

    print(f"Seeded {len(providers)} providers.")
    print(f"Seeded {len(all_slots)} availability slots ({SEED_DAYS} weekdays × {len(SLOT_HOURS)} slots each).")


if __name__ == "__main__":
    asyncio.run(main())
