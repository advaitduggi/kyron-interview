import os
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from tools import book_appointment, get_availability, get_provider_info, lookup_office_info

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """
You are a helpful assistant for a medical practice. You are NOT a doctor and cannot provide medical advice, diagnoses, or treatment recommendations.

Your job is to help patients with:
1. Scheduling appointments with the right doctor
2. Checking prescription refill status
3. Finding office hours and location

Workflow:
- First, warmly greet the patient and collect their full name, date of birth, phone number, and email address.
- Ask what they'd like help with today.
- If scheduling: ask which body part or condition they want treated, then use get_availability to find open slots.
- Always use tools to check real availability — never guess or make up time slots.
- Confirm all details with the patient before calling book_appointment.
- After booking, offer to send a confirmation email and (if they opt in) an SMS reminder.

Safety rules:
- Never recommend medications, dosages, or treatments.
- If a patient describes an emergency, immediately tell them to call 911 or go to the ER.
- Do not speculate about diagnoses.
- Keep responses concise and professional.
"""

ALL_TOOL_DEFINITIONS: list[dict] = [
    get_availability.TOOL_DEFINITION,
    book_appointment.TOOL_DEFINITION,
    get_provider_info.TOOL_DEFINITION,
    lookup_office_info.TOOL_DEFINITION,
]

# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

_TOOL_EXECUTORS = {
    "get_availability": get_availability.execute,
    "book_appointment": book_appointment.execute,
    "get_provider_info": get_provider_info.execute,
    "lookup_office_info": lookup_office_info.execute,
}


async def _execute_tools(
    content: list[Any], db: AsyncSession
) -> list[dict]:
    """Execute all tool_use blocks in a response content list in order.

    Returns a list of tool_result dicts ready to be sent back as a user turn.
    """
    results = []
    for block in content:
        if block.type != "tool_use":
            continue
        executor = _TOOL_EXECUTORS.get(block.name)
        if executor is None:
            tool_result: Any = {"error": f"Unknown tool: {block.name}"}
        else:
            try:
                tool_result = await executor(block.input, db)
            except Exception as exc:  # noqa: BLE001
                tool_result = {"error": str(exc)}

        results.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(tool_result) if not isinstance(tool_result, (dict, list)) else tool_result,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_text(response: anthropic.types.Message) -> str:
    """Return the text of the first text block in a response, or '' if absent."""
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def _serialize_messages(messages: list) -> list:
    """Convert any Anthropic SDK objects in a messages list to plain dicts.

    The SDK returns typed objects (TextBlock, ToolUseBlock, etc.) for assistant
    content blocks. These are not JSON-serialisable, so we must flatten them
    before writing conversation_state to the database.
    """
    result = []
    for msg in messages:
        if isinstance(msg.get("content"), list):
            content = []
            for block in msg["content"]:
                if hasattr(block, "model_dump"):
                    content.append(block.model_dump())
                elif hasattr(block, "__dict__"):
                    content.append(vars(block))
                else:
                    content.append(block)
            result.append({"role": msg["role"], "content": content})
        else:
            result.append(msg)
    return result


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def run_turn(messages: list[dict], db: AsyncSession) -> str:
    """Run one patient turn through the agentic loop.

    Appends intermediate assistant + tool-result turns to `messages` in-place
    so the caller's list stays up-to-date for session persistence.

    Returns the final text reply to surface to the patient.
    """
    client = _get_client()

    while True:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=ALL_TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            # Persist the final assistant message before returning.
            messages.append({"role": "assistant", "content": response.content})
            messages[:] = _serialize_messages(messages)
            return extract_text(response)

        if response.stop_reason == "tool_use":
            tool_results = await _execute_tools(response.content, db)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            # Loop — Claude will process tool results and either call more tools
            # or produce its final end_turn response.
            continue

        # Unexpected stop reason (e.g. "max_tokens") — surface whatever text exists.
        messages.append({"role": "assistant", "content": response.content})
        messages[:] = _serialize_messages(messages)
        return extract_text(response)
