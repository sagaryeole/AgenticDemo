from google.adk.agents import Agent
from google.adk.tools import ToolContext
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent34"  # lets AGENT34_MODEL_PROVIDER override the global choice


# State keys have SCOPES, chosen by a prefix:
#   "user:books"    belongs to the USER: every session of this user sees it (here: the reading log)
#   "chat_topic"    no prefix: belongs to this ONE session only
#   "app:..."       shared by all users of the app (not used here)
#   "temp:..."      thrown away after the current turn (not used here)
def log_book(title: str, rating: int, tool_context: ToolContext) -> dict:
    """Adds a finished book to the user's reading log.

    Args:
        title: The book title.
        rating: The user's rating from 1 to 5.
    """
    books = list(tool_context.state.get("user:books", []))
    books.append({"title": title, "rating": rating})
    tool_context.state["user:books"] = books
    return {"status": "logged", "books_in_log": len(books)}


def get_reading_log(tool_context: ToolContext) -> dict:
    """Returns every book in the user's reading log, from all conversations."""
    return {"books": tool_context.state.get("user:books", [])}


def set_chat_topic(topic: str, tool_context: ToolContext) -> dict:
    """Remembers what THIS conversation is about, e.g. 'holiday reading'. Only this conversation can see it.

    Args:
        topic: A few words describing the conversation.
    """
    tool_context.state["chat_topic"] = topic
    return {"status": "ok"}


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A reading-log assistant.",
    instruction=(
        "You keep the user's reading log. When they finish a book, call log_book with the title and a rating from 1 to 5 (ask if "
        "they did not give one). For questions about what they have read, call get_reading_log and answer only from it. "
        "If the user says what this conversation is about, call set_chat_topic. "
        "This conversation's topic, if any: {chat_topic?}. Keep answers short."
    ),
    tools=[log_book, get_reading_log, set_chat_topic],
)
