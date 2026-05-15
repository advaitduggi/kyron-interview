from sqlalchemy.ext.asyncio import AsyncSession

TOOL_DEFINITION = {
    "name": "lookup_office_info",
    "description": (
        "Look up static information about the medical practice: "
        "address, phone number, office hours, parking, and insurance."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "What the patient is asking about, e.g. "
                    "'hours', 'address', 'parking', 'insurance', 'phone'."
                ),
            },
        },
        "required": ["query"],
    },
}

PRACTICE_INFO: dict[str, str] = {
    "address": "1234 Medical Plaza Drive, Suite 100, San Francisco, CA 94102",
    "phone": "(415) 555-0100",
    "hours": "Monday through Friday, 9:00 AM – 5:00 PM. Closed weekends and federal holidays.",
    "parking": "Free parking is available in the adjacent garage. Enter from Oak Street. Validated for up to 2 hours.",
    "insurance": "We accept most major insurance plans including Aetna, BlueCross BlueShield, Cigna, United Healthcare, and Medicare. Please call ahead to verify your specific plan.",
    "fax": "(415) 555-0199",
    "email": "appointments@kyronmedical.com",
    "website": "https://kyronmedical.com",
}

# Ordered from most specific to least so multi-word queries match well
_KEYWORD_MAP: list[tuple[str, str]] = [
    ("address",   "address"),
    ("location",  "address"),
    ("direction", "address"),
    ("phone",     "phone"),
    ("call",      "phone"),
    ("number",    "phone"),
    ("hour",      "hours"),
    ("open",      "hours"),
    ("close",     "hours"),
    ("time",      "hours"),
    ("schedule",  "hours"),
    ("park",      "parking"),
    ("garage",    "parking"),
    ("insur",     "insurance"),
    ("plan",      "insurance"),
    ("accept",    "insurance"),
    ("cover",     "insurance"),
    ("fax",       "fax"),
    ("email",     "email"),
    ("website",   "website"),
    ("web",       "website"),
    ("site",      "website"),
]


async def execute(args: dict, db: AsyncSession) -> dict:
    query = args.get("query", "").lower()

    for keyword, info_key in _KEYWORD_MAP:
        if keyword in query:
            return {"key": info_key, "value": PRACTICE_INFO[info_key]}

    # No specific match — return everything
    return {"info": PRACTICE_INFO}
