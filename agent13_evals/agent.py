from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent13"  # lets AGENT13_MODEL_PROVIDER override the global choice

BOOKS = {
    "B001": {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "available": True},
    "B002": {"title": "The Fellowship of the Ring", "author": "J.R.R. Tolkien", "year": 1954, "available": False},
    "B003": {"title": "Dune", "author": "Frank Herbert", "year": 1965, "available": True},
    "B004": {"title": "Neuromancer", "author": "William Gibson", "year": 1984, "available": True},
    "B005": {"title": "Foundation", "author": "Isaac Asimov", "year": 1951, "available": False},
}


def list_books() -> list[dict]:
    """List every book in the catalogue with its id, title, author and availability."""
    return [{"id": i, "title": b["title"], "author": b["author"], "available": b["available"]} for i, b in BOOKS.items()]


def find_books_by_author(author: str) -> list[dict]:
    """Find books whose author name contains the given text, ignoring case.

    Args:
        author: Full or partial author name, e.g. 'Tolkien'.
    """
    needle = author.lower()
    return [{"id": i, **b} for i, b in BOOKS.items() if needle in b["author"].lower()]


def get_book(book_id: str) -> dict:
    """Get the details of one book by its id, e.g. 'B003'.

    Args:
        book_id: The catalogue id, like 'B003'.
    """
    book = BOOKS.get(book_id.upper())
    if book is None:
        return {"error": f"No book with id {book_id}"}
    return {"id": book_id.upper(), **book}


# This agent is the thing being TESTED. The tests are in bookshop.evalset.json
# and test_config.json, next to this file.
root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A bookshop assistant that answers from a small catalogue.",
    instruction=(
        "You are a bookshop assistant. Use the catalogue tools to answer questions about books. "
        "Answer only from tool results; if a book is not in the catalogue, say so. "
        "Say clearly whether a book is available. "
        "Questions that are not about this catalogue need no tool; answer them briefly."
    ),
    tools=[list_books, find_books_by_author, get_book],
)
