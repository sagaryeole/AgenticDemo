import sys
from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent12"  # lets AGENT12_MODEL_PROVIDER override the global choice

SERVER_PATH = Path(__file__).parent / "library_server.py"

# McpToolset starts the server as a child process, asks it which tools it has,
# and gives those tools to the agent. None of them are written in this file.
library_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,  # same Python (the uv venv) that runs the agent
            args=[str(SERVER_PATH)],
        ),
        timeout=30,
    ),
    # Optional: expose only some of the server's tools to the model.
    # tool_filter=["list_books", "get_book"],
)

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A librarian assistant that uses an MCP catalogue server.",
    instruction=(
        "You are a librarian. Use the catalogue tools to answer questions about books. "
        "Answer only from tool results; if a book is not in the catalogue, say so. "
        "Say clearly whether a book is available."
    ),
    tools=[library_tools],
)
