"""The REMOTE agent: a shipping-quote specialist, served over the A2A protocol as its own web service.

Start it in a SEPARATE terminal, from the project root, BEFORE running the client agent:

    uv run uvicorn agent27_a2a.remote_server:a2a_app --port 8001

The server uses the model from MODEL_PROVIDER, like every agent here. It can differ from the client's, for example
`MODEL_PROVIDER=gemini uv run uvicorn ...` for the server and `MODEL_PROVIDER=local uv run adk run agent27_a2a` for the client.
Add `PYTHONUNBUFFERED=1` in front if you want its `print` lines to appear immediately.

Check it is up: open http://localhost:8001/.well-known/agent-card.json  (the agent's "business card").
The client agent (agent.py) never imports this file. It only knows the URL.
"""
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from common.models import get_model

PORT = 8001

# Prices in dollars: a base price plus a price per kilogram, by destination.
RATES = {"domestic": (5.0, 1.5), "europe": (12.0, 2.5), "world": (25.0, 4.0)}


def get_shipping_quote(weight_kg: float, destination: str) -> dict:
    """Returns the price to ship a parcel.

    Args:
        weight_kg: The parcel weight in kilograms.
        destination: One of 'domestic', 'europe' or 'world'.
    """
    rate = RATES.get(destination.strip().lower())
    if rate is None:
        return {"status": "error", "message": f"Destination must be one of {sorted(RATES)}"}
    base, per_kg = rate
    print(f"[remote shipping agent] quote requested: {weight_kg} kg to {destination}")
    return {"status": "ok", "destination": destination.lower(), "weight_kg": weight_kg, "price_dollars": round(base + per_kg * weight_kg, 2)}


shipping_agent = Agent(
    model=get_model("agent27"),
    name="shipping_agent",
    description="Gives shipping prices for parcels. Ask it for a quote with a weight in kilograms and a destination "
                "(domestic, europe or world).",
    instruction=(
        "You give shipping quotes. Use get_shipping_quote for every quote and report the price in one sentence. "
        "If the weight or destination is missing, ask for it."
    ),
    tools=[get_shipping_quote],
)

# to_a2a wraps the agent in a web application (ASGI) that speaks the A2A protocol and publishes an agent card.
a2a_app = to_a2a(shipping_agent, port=PORT)
