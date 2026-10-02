import os

from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from common.models import get_model  # global model switch, see common/models.py
from agent45_data_analyst.tools import CSV, TOOLS

MODEL_KEY = "agent45"  # lets AGENT45_MODEL_PROVIDER override the global choice

# ANALYSIS_MODE decides how the agent gets its numbers (the same idea as agent22's CODE_MODE, now with a real table):
#   tools  pandas tools do the arithmetic; the model only chooses the tool (default, any model)
#   code   Gemini writes Python and Google runs it in a sandbox (Gemini only). The table is pasted into the instruction, because the sandbox cannot read your files.
#   none   the table is pasted into the instruction and the model answers from its head (to see why the other modes exist)
PROVIDER = (os.environ.get("AGENT45_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER", "gemini")).lower()
MODE = os.environ.get("ANALYSIS_MODE", "tools").lower()
if MODE not in ("tools", "code", "none"):
    raise ValueError(f"ANALYSIS_MODE must be tools, code or none, got {MODE!r}")
if MODE == "code" and PROVIDER != "gemini":
    raise ValueError("ANALYSIS_MODE=code needs Gemini (set MODEL_PROVIDER=gemini).")

TABLE = CSV.read_text()

if MODE == "tools":
    instruction = (
        "You answer questions about a table of student grades (columns student, class, test1, test2, test3) using your tools. "
        "Start with describe_data. For ANY number, ranking or count, call a tool: never calculate or guess yourself. "
        "To compare tests, first make a column with derive_column (for example improvement = test3 - test1), then use top_rows or column_stats on it. "
        "Report the tool's numbers exactly. If the user asks for a chart, call make_bar_chart."
    )
    kwargs = {"tools": TOOLS}
elif MODE == "code":
    instruction = (
        "You answer questions about this table of student grades. Write and run Python code (pandas) for every number; load the table from the text below with io.StringIO.\n\n" + TABLE
    )
    kwargs = {"code_executor": BuiltInCodeExecutor()}
else:
    instruction = "You answer questions about this table of student grades. Answer briefly.\n\n" + TABLE
    kwargs = {}

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Answers questions about a table of student grades with real calculation.",
    instruction=instruction,
    **kwargs,
)
