from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Provider

TOOL_DEFINITION = {
    "name": "get_provider_info",
    "description": (
        "Return information about one or all providers in the practice, "
        "including their specialty and which body parts / conditions they treat."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "provider_id": {
                "type": "string",
                "description": "UUID of a specific provider. Omit to return all providers.",
            },
        },
        "required": [],
    },
}


async def execute(args: dict, db: AsyncSession) -> dict:
    stmt = select(Provider)
    if args.get("provider_id"):
        stmt = stmt.where(Provider.id == args["provider_id"])

    rows = (await db.execute(stmt)).scalars().all()

    providers = [
        {
            "id": p.id,
            "name": p.name,
            "specialty": p.specialty,
            "body_parts": p.body_parts,
            "bio": p.bio,
        }
        for p in rows
    ]

    return {"providers": providers}
