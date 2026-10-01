import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import ToolContext

# LM Studio's OpenAI-compatible server (Developer tab -> Start Server)
LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
os.environ["OPENAI_API_BASE"] = LM_STUDIO_URL
os.environ["OPENAI_API_KEY"] = "lm-studio"


# Session state: tool_context.state is a dict that ADK stores with the session.
# It survives across turns in the same session, and is lost in a new session.
def save_note(note: str, tool_context: ToolContext) -> dict:
    """Saves a note so it can be recalled later in this conversation.

    Args:
        note: The text to remember, e.g. "payments-api deploy is at 14:00".
    """
    notes = list(tool_context.state.get("notes", []))
    notes.append(note)
    tool_context.state["notes"] = notes  # reassign so ADK sees the change
    return {"status": "saved", "total_notes": len(notes)}


def list_notes(tool_context: ToolContext) -> dict:
    """Returns every note saved so far in this conversation."""
    return {"notes": tool_context.state.get("notes", [])}


root_agent = Agent(
    model=LiteLlm(
        model="openai/qwen3.5-9b",
        api_base=LM_STUDIO_URL,
        api_key="lm-studio",
    ),
    name="root_agent",
    description="An assistant that keeps notes for the user.",
    instruction=(
        "You keep notes for the user. When they ask you to remember or note "
        "something, call save_note. When they ask what you have noted or "
        "remembered, call list_notes and answer only from its output. "
        "Never invent notes."
    ),
    tools=[save_note, list_notes],
)
