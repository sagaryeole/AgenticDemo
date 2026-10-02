import os
import re

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner, PlanReActPlanner
from google.genai import types
from agent24_planning.puzzles import parse_clues
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent24"  # lets AGENT24_MODEL_PROVIDER override the global choice

# Two switches, so you can compare ways of getting to a correct answer:
#
# PLANNER_MODE: how the agent is encouraged to think before it answers
#   default      no planner: the model does whatever it normally does (Gemini thinks silently by default)
#   no_thinking  Gemini only: the model's own thinking is switched OFF (a baseline to show what thinking adds)
#   thinking     Gemini only: the model's built-in thinking, with a token budget, and thought summaries included
#   plan_react   any model: a prompt-based planner. The model writes a PLAN, then alternates REASONING and ACTIONS
#                (tool calls), re-plans if needed, and ends with a FINAL ANSWER. It is designed for agents WITH TOOLS.
#
# CHECKER: off (default) or on. "on" gives the agent a check_seating tool that reports which clues a proposed arrangement breaks.
#
# Defaults: Gemini uses the built-in "thinking" planner, a local model uses no planner. In testing plan_react was the least
# reliable mode (see CASES.md), so it is something to try and measure, not the default.
PROVIDER = (os.environ.get("AGENT24_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER", "gemini")).lower()
MODE = os.environ.get("PLANNER_MODE", "thinking" if PROVIDER == "gemini" else "default").lower()
CHECKER = os.environ.get("CHECKER", "off").lower() == "on"

if MODE in ("no_thinking", "thinking") and PROVIDER != "gemini":
    raise ValueError(f"PLANNER_MODE={MODE} needs Gemini (set MODEL_PROVIDER=gemini). Use plan_react or default for a local model.")


def check_seating(order: list[str], clues: str) -> dict:
    """Checks a proposed seating arrangement against the puzzle's clue sentences and says which clues it breaks.

    Args:
        order: The names from seat 1 to the last seat, e.g. ['Ana', 'Ben', 'Cleo'].
        clues: The clue sentences copied exactly from the puzzle, e.g. 'Ana sits next to Ben. Cleo does not sit at either end.'
    """
    seat = {name: i + 1 for i, name in enumerate(order)}
    rules, ignored = [], []
    for sentence in re.split(r"(?<=\.)\s+", clues.strip()):
        try:
            rules.extend(parse_clues(sentence, len(order)))
        except ValueError:
            ignored.append(sentence)          # a sentence that is not a clue (such as the question) is skipped
    try:
        violated = [text for text, rule in rules if not rule(seat)]
    except KeyError as missing:
        return {"status": "error", "message": f"{missing} is in the clues but not in your order"}
    print(f"[check_seating] {', '.join(order)} -> {'ALL CLUES OK' if not violated else f'{len(violated)} clue(s) broken'}")
    return {"status": "ok", "all_clues_satisfied": not violated, "violated_clues": violated, "clues_checked": len(rules)}


def build_planner():
    if MODE == "default":
        return None
    if MODE == "no_thinking":
        return BuiltInPlanner(thinking_config=types.ThinkingConfig(thinking_budget=0))
    if MODE == "thinking":
        return BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=2048))
    if MODE == "plan_react":
        return PlanReActPlanner()
    raise ValueError(f"PLANNER_MODE must be default, no_thinking, thinking or plan_react, got {MODE!r}")


INSTRUCTION = (
    "You solve logic and scheduling puzzles. Always finish with the single final line the question asks for, "
    "in the form ANSWER: <answer>."
)
if CHECKER:
    INSTRUCTION += (
        " For seating puzzles you have a check_seating tool: propose an arrangement, check it with the exact clue sentences "
        "from the puzzle, and if any clue is broken, fix exactly those and check again. Only give the ANSWER once "
        "check_seating reports that all clues are satisfied."
    )

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A problem solver for logic and scheduling puzzles.",
    instruction=INSTRUCTION,
    tools=[check_seating] if CHECKER else [],
    planner=build_planner(),
)
