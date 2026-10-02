import os
import time

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.plugins.logging_plugin import LoggingPlugin
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent26"  # lets AGENT26_MODEL_PROVIDER override the global choice

# ---------------------------------------------------------------------------------------------------------------
# The agent: two tiny tools, so one question can cause several model calls and tool calls to watch.
# ---------------------------------------------------------------------------------------------------------------
LENGTH_IN_METRES = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0, "inch": 0.0254, "foot": 0.3048, "mile": 1609.344}
WEIGHT_IN_KG = {"g": 0.001, "kg": 1.0, "ounce": 0.0283495, "pound": 0.45359237}


def convert_length(value: float, from_unit: str, to_unit: str) -> dict:
    """Converts a length. Units: mm, cm, m, km, inch, foot, mile.

    Args:
        value: The number to convert.
        from_unit: The unit of the number.
        to_unit: The unit to convert to.
    """
    if from_unit not in LENGTH_IN_METRES or to_unit not in LENGTH_IN_METRES:
        return {"status": "error", "message": f"Units must be one of {sorted(LENGTH_IN_METRES)}"}
    return {"status": "ok", "result": round(value * LENGTH_IN_METRES[from_unit] / LENGTH_IN_METRES[to_unit], 4), "unit": to_unit}


def convert_weight(value: float, from_unit: str, to_unit: str) -> dict:
    """Converts a weight. Units: g, kg, ounce, pound.

    Args:
        value: The number to convert.
        from_unit: The unit of the number.
        to_unit: The unit to convert to.
    """
    if from_unit not in WEIGHT_IN_KG or to_unit not in WEIGHT_IN_KG:
        return {"status": "error", "message": f"Units must be one of {sorted(WEIGHT_IN_KG)}"}
    return {"status": "ok", "result": round(value * WEIGHT_IN_KG[from_unit] / WEIGHT_IN_KG[to_unit], 4), "unit": to_unit}


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Converts lengths and weights.",
    instruction=(
        "You convert lengths and weights. Always use convert_length and convert_weight for the numbers, one call per "
        "conversion, then answer in one short sentence per conversion."
    ),
    tools=[convert_length, convert_weight],
)


# ---------------------------------------------------------------------------------------------------------------
# Observability, part 1: a PLUGIN. A plugin hooks into every agent, model call and tool call of a run (agent callbacks
# like agent11's only cover one agent). This one measures time and tokens and prints a summary when the run ends.
# ---------------------------------------------------------------------------------------------------------------
class RunSummaryPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="run_summary")
        self._reset()

    def _reset(self):
        self.started = time.perf_counter()
        self.model_calls = []   # (seconds, prompt_tokens, output_tokens)
        self.tool_calls = []    # (tool name, seconds)
        self._t = 0.0

    async def before_run_callback(self, *, invocation_context):
        self._reset()
        return None

    async def before_model_callback(self, *, callback_context, llm_request):
        self._t = time.perf_counter()
        return None

    async def after_model_callback(self, *, callback_context, llm_response):
        seconds = time.perf_counter() - self._t
        usage = llm_response.usage_metadata
        prompt = (usage.prompt_token_count or 0) if usage else 0
        output = (usage.candidates_token_count or 0) if usage else 0
        self.model_calls.append((seconds, prompt, output))
        wants_tool = bool(llm_response.content and any(p.function_call for p in (llm_response.content.parts or [])))
        print(f"[trace] model call #{len(self.model_calls)}: {seconds:5.2f}s  in={prompt:>5} tok  out={output:>4} tok"
              f"  -> {'asks for a tool' if wants_tool else 'final answer'}")
        return None

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        self._t = time.perf_counter()
        return None

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        seconds = time.perf_counter() - self._t
        self.tool_calls.append((tool.name, seconds))
        print(f"[trace] tool call  #{len(self.tool_calls)}: {seconds:5.2f}s  {tool.name}({tool_args}) -> {result}")
        return None

    async def after_run_callback(self, *, invocation_context):
        total = time.perf_counter() - self.started
        model_seconds = sum(s for s, _, _ in self.model_calls)
        print("[trace] ---- run summary ----")
        print(f"[trace] model calls: {len(self.model_calls)}  ({model_seconds:.2f}s, "
              f"{sum(p for _, p, _ in self.model_calls)} prompt tokens, {sum(o for _, _, o in self.model_calls)} output tokens)")
        print(f"[trace] tool calls : {len(self.tool_calls)}  ({sum(s for _, s in self.tool_calls) * 1000:.1f} ms in tools)")
        print(f"[trace] wall clock : {total:.2f}s  ({model_seconds / total:.0%} waiting for the model)" if total else "")
        return None


plugins = [RunSummaryPlugin()]

# Part 2 (optional): ADK's own LoggingPlugin prints a detailed log of every event. Turn it on with OBS_LOGGING=1.
if os.environ.get("OBS_LOGGING") == "1":
    plugins.append(LoggingPlugin())

# Part 3 (optional): OpenTelemetry spans. ADK already creates spans for each agent, model call and tool call; they go
# nowhere unless an exporter is configured. OBS_SPANS=1 prints one line per finished span.
if os.environ.get("OBS_SPANS") == "1":
    from agent26_observability.spans import enable_span_printing
    enable_span_printing()

# ADK uses `app` instead of `root_agent` when a module defines one: it is the agent plus application-wide plugins.
app = App(name="agent26_observability", root_agent=root_agent, plugins=plugins)
