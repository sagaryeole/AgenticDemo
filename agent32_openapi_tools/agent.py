from pathlib import Path

from google.adk.agents import Agent
from google.adk.tools.openapi_tool import OpenAPIToolset
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent32"  # lets AGENT32_MODEL_PROVIDER override the global choice

# The API's own description (an OpenAPI "spec"), saved from the running service with `python todo_api.py`.
# It lists every endpoint, its parameters and what it returns. Nothing in this file describes the tools by hand.
SPEC = Path(__file__).resolve().parent / "todo_openapi.json"

# OpenAPIToolset turns each operation in the spec into a tool: list_tasks, add_task, complete_task, delete_task.
# When the model calls one, the toolset sends the real HTTP request to the server named in the spec (localhost:8002).
todo_tools = OpenAPIToolset(spec_str=SPEC.read_text(), spec_str_type="json")


def show_tool_call(tool, args, tool_context):
    """Prints each API call, so you can see the HTTP traffic the agent causes."""
    print(f"[api call] {tool.name}({args})")
    return None


def report_tool_error(tool, args, tool_context, error):
    """If a call fails (for example the service is not running), give the model an error result instead of crashing the run."""
    print(f"[api error] {tool.name}: {type(error).__name__}")
    return {"status": "error", "message": f"Could not reach the to-do service ({type(error).__name__}). Is it running on port 8002?"}


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A to-do list assistant that works through a REST API.",
    instruction=(
        "You manage the user's to-do list using the API tools. Always call list_tasks before saying what is on the list, "
        "and use the task ids it returns. Report what the API actually returned. If a call fails, say what went wrong."
    ),
    tools=[todo_tools],
    before_tool_callback=show_tool_call,
    on_tool_error_callback=report_tool_error,
)
