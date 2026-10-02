import os

from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent25"  # lets AGENT25_MODEL_PROVIDER override the global choice

MENU = {
    "monday": {"dish": "Vegetable soup", "allergens": ["celery"]},
    "tuesday": {"dish": "Chicken satay", "allergens": ["peanuts"]},
    "wednesday": {"dish": "Pasta bolognese", "allergens": ["gluten", "egg"]},
    "thursday": {"dish": "Fish fingers", "allergens": ["fish", "gluten"]},
    "friday": {"dish": "Cheese pizza", "allergens": ["milk", "gluten"]},
}


def get_lunch(day: str) -> dict:
    """Returns the school lunch dish for a weekday.

    Args:
        day: A weekday name such as 'Tuesday'.
    """
    entry = MENU.get(day.strip().lower())
    if entry is None:
        return {"status": "error", "message": f"There is no school lunch on {day}. Lunch is served Monday to Friday."}
    return {"status": "ok", "day": day.strip().capitalize(), "dish": entry["dish"]}


def get_allergens(dish: str) -> dict:
    """Returns the allergens in a lunch dish.

    Args:
        dish: The exact dish name as given by get_lunch, e.g. 'Chicken satay'.
    """
    for entry in MENU.values():
        if entry["dish"].lower() == dish.strip().lower():
            return {"status": "ok", "dish": entry["dish"], "allergens": entry["allergens"]}
    return {"status": "error", "message": f"Unknown dish: {dish}"}


def forget_earlier_turns(callback_context, llm_request):
    """A deliberate BUG you can switch on (FORGET_HISTORY=1): the model only sees the latest user message, not the conversation.

    It keeps the last user message and anything after it (this turn's tool calls and results), and drops everything before.
    Used in CASES.md to show that a multi-turn eval notices lost context.
    """
    contents = llm_request.contents or []
    last_user = max((i for i, c in enumerate(contents) if c.role == "user" and any(p.text for p in (c.parts or []))), default=0)
    llm_request.contents = contents[last_user:]
    return None


# This agent is the thing being TESTED. The tests are lunch.evalset.json and the two config files next to this file.
# What is new compared with agent13: the tests are CONVERSATIONS of several turns, where a later question
# ("Does it contain nuts?") only makes sense given an earlier answer.
root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Answers questions about the school lunch menu and its allergens.",
    instruction=(
        "You answer questions about the school lunch menu. Use get_lunch to find the dish for a day and get_allergens "
        "for allergens. Answer only from tool results, in one or two sentences. Remember what was said earlier in the "
        "conversation: when the user says 'it' or 'that', they mean the dish you just discussed. If a day has no "
        "lunch, say so."
    ),
    tools=[get_lunch, get_allergens],
    before_model_callback=forget_earlier_turns if os.environ.get("FORGET_HISTORY") == "1" else None,
)
