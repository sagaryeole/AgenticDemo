import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.base_toolset import BaseToolset

from common.embeddings import embed_texts
from common.models import get_model  # global model switch, see common/models.py
from agent38_many_tools.tools import ALL_TOOLS

MODEL_KEY = "agent38"  # lets AGENT38_MODEL_PROVIDER override the global choice

# Embeddings follow the chat provider unless EMBEDDING_PROVIDER is set explicitly (same rule as agent20).
os.environ.setdefault("EMBEDDING_PROVIDER", os.environ.get("AGENT38_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER", "gemini"))

# TOOL_MODE chooses how the 20 tools are given to the model:
#   all     all 20, with their proper descriptions (the default)
#   vague   all 20, but every description replaced by "A helper function."  (the names stay)
#   routed  only the TOP_N tools whose description is closest in meaning to the user's message (embeddings, labs 17-18)
TOOL_MODE = os.environ.get("TOOL_MODE", "all")
TOP_N = int(os.environ.get("TOP_N", "4"))


def show_tool_call(tool, args, tool_context):
    """Prints each tool call, so you can see which tool the model chose."""
    print(f"[tool call] {tool.name}({args})")
    return None


ERRORS = []  # one entry per failed tool call, so the test script can count them


def report_tool_error(tool, args, tool_context, error):
    """A tool that fails (for example on a unit it does not know) gives the model an error result instead of crashing the run."""
    ERRORS.append(tool.name)
    print(f"[tool error] {tool.name}: {type(error).__name__}: {error}")
    return {"error": f"{tool.name} failed with {type(error).__name__}: {error}"}


def vague_version(function):
    """The same function with its docstring replaced. ADK builds the tool description from the docstring, so the model sees nothing useful."""
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)
    wrapper.__name__, wrapper.__signature__ = function.__name__, __import__("inspect").signature(function)
    wrapper.__annotations__ = function.__annotations__
    wrapper.__doc__ = "A helper function."
    return wrapper


class NearestTools(BaseToolset):
    """A toolset that offers only the few tools that fit the user's message. ADK asks it for tools before EVERY model call
    (get_tools), so the choice can depend on the message. The model never sees the other tools, so it cannot pick them."""

    def __init__(self, functions, top_n: int):
        super().__init__()
        self.tools = [FunctionTool(f) for f in functions]
        self.top_n = top_n
        self.vectors = embed_texts([f"{t.name}: {t.description}" for t in self.tools], kind="document")

    async def get_tools(self, readonly_context=None):
        content = readonly_context.user_content if readonly_context else None
        message = "".join(p.text or "" for p in content.parts) if content and content.parts else ""
        if not message:
            return self.tools
        scores = self.vectors @ embed_texts([message], kind="query")[0]
        chosen = [self.tools[i] for i in scores.argsort()[::-1][: self.top_n]]
        print(f"[routing] offered: {[t.name for t in chosen]}")
        return chosen

    async def close(self) -> None:
        return None


if TOOL_MODE == "vague":
    tools = [FunctionTool(vague_version(f)) for f in ALL_TOOLS]
elif TOOL_MODE == "routed":
    tools = [NearestTools(ALL_TOOLS, TOP_N)]
else:
    tools = [FunctionTool(f) for f in ALL_TOOLS]

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A study helper with 20 small tools: conversions, percentages, dates, text and random numbers.",
    instruction=(
        "You are a study helper. For any calculation, conversion, date question, text question or random pick, call the "
        "fitting tool and give its result in one short sentence. Never calculate in your head."
    ),
    tools=tools,
    before_tool_callback=show_tool_call,
    on_tool_error_callback=report_tool_error,
)
