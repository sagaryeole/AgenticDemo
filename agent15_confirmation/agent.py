from google.adk.agents import Agent
from google.adk.tools import FunctionTool, ToolContext
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent15"  # lets AGENT15_MODEL_PROVIDER override the global choice
LARGE_GROUP = 6  # bookings for MORE than this many people need a human to approve


def _reservations(tool_context: ToolContext) -> dict:
    """Returns this session's reservations, creating two sample ones the first time."""
    if "reservations" not in tool_context.state:
        tool_context.state["reservations"] = {
            "R1": {"name": "Maria", "people": 2, "time": "Friday 19:00"},
            "R2": {"name": "Chen", "people": 4, "time": "Saturday 20:00"},
        }
    return dict(tool_context.state["reservations"])


def list_reservations(tool_context: ToolContext) -> dict:
    """Lists all current reservations with their ids."""
    return {"reservations": _reservations(tool_context)}


def make_reservation(name: str, people: int, time: str, tool_context: ToolContext) -> dict:
    """Books a table.

    Args:
        name: Name for the reservation.
        people: Number of guests.
        time: When, e.g. 'Sunday 18:30'.
    """
    reservations = _reservations(tool_context)
    new_id = f"R{len(reservations) + 1}"
    while new_id in reservations:
        new_id += "x"
    reservations[new_id] = {"name": name, "people": people, "time": time}
    tool_context.state["reservations"] = reservations  # reassign so ADK sees the change
    return {"status": "booked", "id": new_id, **reservations[new_id]}


def cancel_reservation(reservation_id: str, tool_context: ToolContext) -> dict:
    """Cancels a reservation. This cannot be undone.

    Args:
        reservation_id: The id from list_reservations, e.g. 'R1'.
    """
    reservations = _reservations(tool_context)
    removed = reservations.pop(reservation_id.upper(), None)
    if removed is None:
        return {"status": "error", "message": f"No reservation {reservation_id}"}
    tool_context.state["reservations"] = reservations
    return {"status": "cancelled", "id": reservation_id.upper(), **removed}


# require_confirmation=True: ADK pauses BEFORE the function runs and asks a human.
# If the human says no, the function is never called.
cancel_tool = FunctionTool(cancel_reservation, require_confirmation=True)


# require_confirmation can also be a function. It receives the SAME arguments the model chose (and the
# tool_context, hence **kwargs) and returns True when a human must approve. Here only large groups need
# approval; small bookings go straight through.
def needs_approval(people: int, **kwargs) -> bool:
    return people > LARGE_GROUP


book_tool = FunctionTool(make_reservation, require_confirmation=needs_approval)

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A restaurant reservation assistant.",
    instruction=(
        "You manage table reservations. Use list_reservations to see bookings, make_reservation to book, "
        "and cancel_reservation to cancel. Always use the tools; never guess what is booked. "
        "If an action is not approved, tell the user it was not done."
    ),
    tools=[list_reservations, book_tool, cancel_tool],
)
