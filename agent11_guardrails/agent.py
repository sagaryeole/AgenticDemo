import re
from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent11"  # lets AGENT11_MODEL_PROVIDER override the global choice

MENU = {"margherita": 9, "pepperoni": 11, "veggie": 10}  # price per pizza
MAX_PIZZAS = 10

# A card number is 13-16 digits, optionally split by spaces or dashes.
CARD_PATTERN = re.compile(r"\b(?:\d[ -]?){13,16}\b")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_PATTERN = re.compile(r"\b\d{3}[-.\s]\d{4}\b")


def get_menu() -> dict:
    """Returns the pizzas on the menu with the price of each one in dollars."""
    return {"menu": MENU}


def place_order(item: str, quantity: int) -> dict:
    """Places an order for pizzas.

    Args:
        item: The pizza name from the menu, e.g. 'margherita'.
        quantity: How many pizzas to order.
    """
    price = MENU[item.lower()]
    return {
        "status": "confirmed",
        "order_id": "A123",
        "item": item.lower(),
        "quantity": quantity,
        "total_dollars": price * quantity,
        # Internal detail that should never reach customers:
        "internal_note": "Kitchen contact: kitchen@pizzaplace.example or 555-0142",
    }


# 1. BEFORE the model: runs on every model request. Returning an LlmResponse skips
#    the model call entirely. Returning None lets the request go through.
def block_card_numbers(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    last_user_text = ""
    for content in reversed(llm_request.contents or []):
        if content.role == "user":
            text = " ".join(p.text for p in (content.parts or []) if p.text)
            if text:  # skip tool results, which are also sent as 'user' content
                last_user_text = text
                break
    if CARD_PATTERN.search(last_user_text) or "cvv" in last_user_text.lower():
        callback_context.state["blocked_count"] = callback_context.state.get("blocked_count", 0) + 1
        print("[guardrail] model call BLOCKED: message looks like it contains card details")
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Please don't share card details in this chat. You can pay when your order arrives. Tell me what you'd like to order.")],
            )
        )
    return None


# 2. BEFORE a tool: runs with the arguments the model chose. Returning a dict
#    replaces the tool result and the real function is never called.
def validate_order(tool: BaseTool, args: dict, tool_context: ToolContext) -> Optional[dict]:
    if tool.name != "place_order":
        return None
    item, quantity = str(args.get("item", "")).lower(), args.get("quantity")
    if item not in MENU:
        print(f"[guardrail] tool call BLOCKED: '{item}' is not on the menu")
        return {"status": "error", "message": f"'{item}' is not on the menu. Available: {', '.join(MENU)}."}
    if not isinstance(quantity, int) or not 1 <= quantity <= MAX_PIZZAS:
        print(f"[guardrail] tool call BLOCKED: quantity {quantity} is outside 1-{MAX_PIZZAS}")
        return {"status": "error", "message": f"Quantity must be between 1 and {MAX_PIZZAS}. Larger orders need a phone call to the shop."}
    return None


# 3. AFTER the model: runs on every model reply. Here it hides staff contact details.
def hide_staff_contacts(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    parts = llm_response.content.parts if llm_response.content else []
    if not parts or any(p.function_call for p in parts):
        return None  # leave tool requests alone
    text = " ".join(p.text for p in parts if p.text)
    cleaned = PHONE_PATTERN.sub("[number removed]", EMAIL_PATTERN.sub("[email removed]", text))
    if cleaned == text:
        return None
    print("[guardrail] reply MODIFIED: staff contact details removed")
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=cleaned)]))


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A pizza-ordering assistant with guardrails.",
    instruction=(
        "You take pizza orders. Use get_menu to show the menu and place_order to order. "
        "Always confirm the order id and total after ordering. If a tool result contains "
        "an internal note, you may pass on the kitchen contact if the customer asks for it."
    ),
    tools=[get_menu, place_order],
    before_model_callback=block_card_numbers,
    before_tool_callback=validate_order,
    after_model_callback=hide_staff_contacts,
)
