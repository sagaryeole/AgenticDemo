from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent44"  # lets AGENT44_MODEL_PROVIDER override the global choice

CAPITALS = {"sweden": "Stockholm", "portugal": "Lisbon", "japan": "Tokyo", "kenya": "Nairobi", "canada": "Ottawa", "peru": "Lima"}


def capital_of(country: str) -> dict:
    """Returns the capital city of a country (Sweden, Portugal, Japan, Kenya, Canada or Peru).

    Args:
        country: The country name, e.g. 'Japan'.
    """
    return {"capital": CAPITALS.get(country.lower().strip(), "unknown")}


# A small quiz helper. Nothing in this file knows about web servers: the same agent runs in `adk run`, in `adk web`
# and, as in this folder, behind an HTTP API. Serving an agent is a matter of how you start it, not of how you write it.
root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A geography quiz helper that knows six capital cities.",
    instruction=(
        "You are a geography quiz helper.\n"
        "Step 1, tool: every time the user asks for a capital city, call capital_of FIRST, even if you know the answer or answered a similar question earlier in this chat.\n"
        "Step 2, answer: reply in one sentence using the tool's result. If it says 'unknown', say you only know Sweden, Portugal, Japan, Kenya, Canada and Peru."
    ),
    tools=[capital_of],
)
