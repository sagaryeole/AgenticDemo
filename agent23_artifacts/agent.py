from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.genai import types
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent23"  # lets AGENT23_MODEL_PROVIDER override the global choice


# An ARTIFACT is a named file (text, image, PDF...) that belongs to a session or a user, and ADK keeps every saved
# version. It is the right place for a document the agent PRODUCES, as opposed to state (small values) or memory (facts).
# In `adk run` the files land in agent23_artifacts/.adk/artifacts/ (look there). In `adk web` they appear in the UI.

async def save_document(filename: str, content: str, tool_context: ToolContext) -> dict:
    """Saves a text document. Saving the same filename again creates a NEW VERSION; older versions are kept.

    Args:
        filename: A short name ending in .md, e.g. 'trip_plan.md'. A name starting with 'user:' (e.g. 'user:trip_plan.md')
            is kept for this user across conversations; other names belong to this conversation only.
        content: The full text of the document (markdown).
    """
    part = types.Part.from_bytes(data=content.encode("utf-8"), mime_type="text/markdown")
    version = await tool_context.save_artifact(filename, part)
    print(f"[artifact] saved {filename} version {version} ({len(content)} characters)")
    return {"status": "saved", "filename": filename, "version": version}


async def list_documents(tool_context: ToolContext) -> dict:
    """Lists the documents saved in this conversation, and the user's own 'user:' documents."""
    return {"filenames": await tool_context.list_artifacts()}


async def read_document(filename: str, tool_context: ToolContext, version: int = -1) -> dict:
    """Reads a saved document.

    Args:
        filename: The name used when saving, e.g. 'trip_plan.md'.
        version: Which version to read, starting at 0 for the first save. Leave out (or use -1) for the latest.
    """
    part = await tool_context.load_artifact(filename, None if version < 0 else version)
    if part is None or part.inline_data is None:
        return {"status": "error", "message": f"No document {filename!r} (version {version if version >= 0 else 'latest'})"}
    return {"status": "ok", "filename": filename, "content": part.inline_data.data.decode("utf-8")}


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A planning assistant that keeps its work as saved, versioned documents.",
    instruction=(
        "You help the user plan things (trips, study schedules, shopping lists) and keep the plan as a markdown document. "
        "When you create or change a plan, call save_document with the COMPLETE updated text, using the filename "
        "'plan.md' unless the user names another. Before changing an existing plan, call read_document to get its current "
        "text. When the user asks to see an older version, call read_document with that version number (0 is the first). "
        "Use list_documents to see what exists. Tell the user the filename and version number after every save. "
        "Never claim a document exists without checking."
    ),
    tools=[save_document, list_documents, read_document],
)
