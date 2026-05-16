from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Availability, Provider

TOOL_DEFINITION = {
    "name": "get_availability",
    "description": (
        "Query open appointment slots. Filter by provider and/or body part. "
        "Always call this tool — never guess or invent time slots."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "provider_id": {
                "type": "string",
                "description": "UUID of a specific provider. Omit to search all providers.",
            },
            "body_part": {
                "type": "string",
                "description": (
                    "Body part or condition the patient described "
                    "(e.g. 'knee', 'heart'). Used to filter to relevant providers."
                ),
            },
            "date_range_start": {
                "type": "string",
                "description": "ISO 8601 date string (YYYY-MM-DD). Start of the search window (inclusive).",
            },
            "date_range_end": {
                "type": "string",
                "description": "ISO 8601 date string (YYYY-MM-DD). End of the search window (inclusive).",
            },
        },
        "required": ["date_range_start", "date_range_end"],
    },
}

EASTERN = timezone(timedelta(hours=-4))  # EDT

_MAX_RESULTS = 10
# Fetch more rows than needed so Python-side body_part filtering has enough to
# work with before we cap at _MAX_RESULTS.
_PREFETCH = 200


async def execute(args: dict, db: AsyncSession) -> dict:
    date_start = datetime.fromisoformat(args["date_range_start"]).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )
    date_end = datetime.fromisoformat(args["date_range_end"]).replace(
        hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
    )

    stmt = (
        select(Availability, Provider)
        .join(Provider, Availability.provider_id == Provider.id)
        .where(
            and_(
                Availability.is_booked.is_(False),
                Availability.slot_time >= date_start,
                Availability.slot_time <= date_end,
            )
        )
        .order_by(Availability.slot_time)
        .limit(_PREFETCH)
    )

    if args.get("provider_id"):
        stmt = stmt.where(Provider.id == args["provider_id"])

    rows = (await db.execute(stmt)).all()

    # Python-side body_part filter — works on both SQLite and PostgreSQL since
    # body_parts is a plain Python list after the ORM deserialises the JSON column.
    if args.get("body_part"):
        term = args["body_part"].lower()
        rows = [
            (avail, provider)
            for avail, provider in rows
            if any(term in bp.lower() for bp in (provider.body_parts or []))
        ]

    slots = [
        {
            "slot_id": avail.id,
            "provider_id": avail.provider_id,
            "provider_name": provider.name,
            "specialty": provider.specialty,
            "slot_time": avail.slot_time.astimezone(EASTERN).strftime("%A, %B %-d at %-I:%M %p ET"),
        }
        for avail, provider in rows[:_MAX_RESULTS]
    ]

    return {"slots": slots, "count": len(slots)}
