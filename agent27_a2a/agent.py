import os

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent27"  # lets AGENT27_MODEL_PROVIDER override the global choice

# Where the remote agent lives. The agent card is its public description: name, skills, and how to call it.
REMOTE_URL = os.environ.get("SHIPPING_AGENT_URL", "http://localhost:8001")

# From this agent's point of view, the shipping specialist is just another sub-agent. But it runs in a DIFFERENT PROCESS
# (it could be on another machine, written by another team, using another framework). Only the URL is shared.
shipping_service = RemoteA2aAgent(
    name="shipping_service",
    description="A remote agent that gives shipping prices for parcels (weight in kg, destination domestic, europe or world).",
    agent_card=f"{REMOTE_URL}/.well-known/agent-card.json",
)

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="shop_assistant",
    description="A shop assistant that can quote shipping.",
    instruction=(
        "You are a friendly shop assistant. For any question about shipping prices, transfer to shipping_service. "
        "Answer other questions yourself, briefly."
    ),
    sub_agents=[shipping_service],
)
