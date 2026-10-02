import json
import os
import re
from datetime import date
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools import ToolContext
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent21"  # lets AGENT21_MODEL_PROVIDER override the global choice

# Long-term memory lives in a file, so it survives a restart. (Session state, agent05, is lost when the session ends.)
# Set MEMORY_FILE to use another file, for example to start with an empty memory.
MEMORY_FILE = Path(os.environ.get("MEMORY_FILE", Path(__file__).resolve().parent / "memory.json"))


def _load() -> dict:
    return json.loads(MEMORY_FILE.read_text()) if MEMORY_FILE.exists() else {}


def _save(data: dict) -> None:
    MEMORY_FILE.write_text(json.dumps(data, indent=2))


def remember(fact: str, tool_context: ToolContext) -> dict:
    """Saves one lasting fact about the user so it can be recalled in future conversations.

    Args:
        fact: A short, self-contained fact, e.g. 'Chemistry exam is on 14 November' or 'Prefers short explanations'.
    """
    data = _load()
    facts = data.setdefault(tool_context.user_id, [])
    next_id = max((f["id"] for f in facts), default=0) + 1
    facts.append({"id": next_id, "fact": fact, "saved": date.today().isoformat()})
    _save(data)
    return {"status": "saved", "id": next_id}


def recall(topic: str, tool_context: ToolContext) -> dict:
    """Looks up saved facts about the user. Call it at the start of a conversation, and when the user asks what you know.

    Args:
        topic: A word or phrase to search for, e.g. 'exam'. Use an empty string to get every saved fact.
    """
    facts = _load().get(tool_context.user_id, [])
    words = set(re.findall(r"\w+", topic.lower()))
    if words:
        facts = [f for f in facts if words & set(re.findall(r"\w+", f["fact"].lower()))]
    return {"facts": facts}


def forget(fact_id: int, tool_context: ToolContext) -> dict:
    """Deletes one saved fact, by the id shown by recall.

    Args:
        fact_id: The id of the fact to delete.
    """
    data = _load()
    facts = data.get(tool_context.user_id, [])
    kept = [f for f in facts if f["id"] != fact_id]
    if len(kept) == len(facts):
        return {"status": "error", "message": f"No saved fact with id {fact_id}"}
    data[tool_context.user_id] = kept
    _save(data)
    return {"status": "deleted", "id": fact_id}


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A study buddy that remembers you between conversations.",
    instruction=(
        "You are a friendly study buddy. At the START of every conversation, call recall with an empty topic to "
        "load what you already know about the user, and use it naturally (for example keep explanations short if "
        "they prefer that). When the user tells you something lasting about themselves (an exam date, a subject, a "
        "goal, how they like to learn), call remember with one short fact. Do not save small talk, and do not save "
        "the same fact twice. If the user asks you to forget something, call recall to find it and then forget. "
        "Never claim to remember something that recall did not return."
    ),
    tools=[remember, recall, forget],
)
