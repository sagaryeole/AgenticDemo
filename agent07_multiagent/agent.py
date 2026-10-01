from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent07"  # lets AGENT07_MODEL_PROVIDER override the global choice


def get_weather(city: str) -> dict:
    """Returns the current weather for a city.

    Args:
        city: City name, e.g. 'Paris' or 'Tokyo'.
    """
    fake = {
        "paris": {"temp_c": 18, "condition": "cloudy"},
        "tokyo": {"temp_c": 26, "condition": "sunny"},
        "stockholm": {"temp_c": 9, "condition": "rainy"},
    }
    data = fake.get(city.lower())
    if data is None:
        return {"status": "error", "message": f"No weather data for {city}"}
    return {"status": "success", "city": city, **data}


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Converts an amount between currencies using fixed demo rates.

    Args:
        amount: The amount to convert.
        from_currency: Three-letter code, e.g. 'USD'.
        to_currency: Three-letter code, e.g. 'EUR'.
    """
    per_usd = {"USD": 1.0, "EUR": 0.9, "JPY": 150.0, "SEK": 10.5}
    src, dst = from_currency.upper(), to_currency.upper()
    if src not in per_usd or dst not in per_usd:
        return {"status": "error", "message": f"Supported currencies: {', '.join(per_usd)}"}
    result = amount / per_usd[src] * per_usd[dst]
    return {"status": "success", "result": round(result, 2), "currency": dst}


# Specialists: each has one narrow job and one tool. The description is what the
# coordinator reads when it decides who to hand a request to.
weather_agent = Agent(
    name="weather_agent",
    model=get_model(MODEL_KEY),
    description="Gives the current weather for a city.",
    instruction="Call get_weather for the city the user names and report exactly what it returns. Never invent weather data.",
    tools=[get_weather],
)

currency_agent = Agent(
    name="currency_agent",
    model=get_model(MODEL_KEY),
    description="Converts money between currencies.",
    instruction="Call convert_currency with the amount and currency codes the user gives, and report the result. Never guess a rate.",
    tools=[convert_currency],
)

# Coordinator: has no tools of its own, only sub_agents it can transfer to.
root_agent = Agent(
    name="root_agent",
    model=get_model(MODEL_KEY),
    description="Travel helper that routes questions to the right specialist.",
    instruction=(
        "You are a travel helper. For weather questions, transfer to weather_agent. "
        "For money or currency conversion, transfer to currency_agent. "
        "Answer anything else yourself."
    ),
    sub_agents=[weather_agent, currency_agent],
)
