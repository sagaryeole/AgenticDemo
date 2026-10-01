"""A tiny MCP server: a library catalogue. It runs as its OWN process.

The agent starts it and talks to it over stdin/stdout, so never print() here;
stray output on stdout would corrupt the protocol. Use stderr for debugging.
"""
from mcp.server.mcpserver import MCPServer

server = MCPServer("library-catalogue")

BOOKS = {
    "B001": {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "available": True},
    "B002": {"title": "The Fellowship of the Ring", "author": "J.R.R. Tolkien", "year": 1954, "available": False},
    "B003": {"title": "Dune", "author": "Frank Herbert", "year": 1965, "available": True},
    "B004": {"title": "Neuromancer", "author": "William Gibson", "year": 1984, "available": True},
    "B005": {"title": "Foundation", "author": "Isaac Asimov", "year": 1951, "available": False},
}


# The function name, type hints and docstring become the tool schema the model sees,
# exactly like a normal ADK function tool (agent04).
@server.tool()
def list_books() -> list[dict]:
    """List every book in the catalogue with its id, title, author and availability."""
    return [{"id": i, "title": b["title"], "author": b["author"], "available": b["available"]} for i, b in BOOKS.items()]


@server.tool()
def find_books_by_author(author: str) -> list[dict]:
    """Find books whose author name contains the given text, ignoring case.

    Args:
        author: Full or partial author name, e.g. 'Tolkien'.
    """
    needle = author.lower()
    return [{"id": i, **b} for i, b in BOOKS.items() if needle in b["author"].lower()]


@server.tool()
def get_book(book_id: str) -> dict:
    """Get the details of one book by its id, e.g. 'B003'.

    Args:
        book_id: The catalogue id, like 'B003'.
    """
    book = BOOKS.get(book_id.upper())
    if book is None:
        return {"error": f"No book with id {book_id}"}
    return {"id": book_id.upper(), **book}


if __name__ == "__main__":
    server.run(transport="stdio")
