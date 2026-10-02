import ast
import math
import operator
import os

from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent22"  # lets AGENT22_MODEL_PROVIDER override the global choice

# CODE_MODE decides how the agent gets exact answers:
#   builtin    Gemini writes Python and Google runs it in a sandbox (Gemini only)
#   calculator two small safe tools (calculate, count_letter) that work with any model
#   none       no help at all: the model answers from its own "head" (use it to see why the other modes exist)
# Default: builtin on Gemini, calculator on a local model.
PROVIDER = (os.environ.get("AGENT22_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER", "gemini")).lower()
MODE = (os.environ.get("CODE_MODE") or ("builtin" if PROVIDER == "gemini" else "calculator")).lower()

if MODE == "builtin" and PROVIDER != "gemini":
    raise ValueError("CODE_MODE=builtin needs Gemini (set MODEL_PROVIDER=gemini). Use CODE_MODE=calculator for a local model.")
if MODE not in ("builtin", "calculator", "none"):
    raise ValueError(f"CODE_MODE must be builtin, calculator or none, got {MODE!r}")


# --- the safe calculator ------------------------------------------------------------------------------
# NEVER pass model text to eval(): it would run any Python the model (or a user) wrote. Instead, parse the text into a
# tree and allow only numbers, the operators below and a few maths functions.
_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_FUNCTIONS = {"sqrt": math.sqrt, "round": round, "abs": abs, "min": min, "max": max}
_MAX_EXPONENT = 10_000  # stops inputs like 9**9**9 from freezing the program


def _evaluate(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("exponent too large")
        return _OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS and not node.keywords:
        return _FUNCTIONS[node.func.id](*[_evaluate(a) for a in node.args])
    raise ValueError("only numbers, + - * / // % **, parentheses and sqrt/round/abs/min/max are allowed")


def calculate(expression: str) -> dict:
    """Calculates an arithmetic expression exactly, for example '48271 * 91357' or '2500 * (1 + 0.037 / 12) ** (12 * 12)'.

    Args:
        expression: Numbers with + - * / // % ** and parentheses. Functions allowed: sqrt, round, abs, min, max.
    """
    try:
        result = _evaluate(ast.parse(expression.strip(), mode="eval").body)
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError, OverflowError) as exc:
        return {"status": "error", "message": str(exc)}
    print(f"[calculate] {expression} = {result}")
    return {"status": "ok", "result": result}


def count_letter(text: str, letter: str) -> dict:
    """Counts how many times one letter appears in a text, ignoring upper and lower case.

    Args:
        text: The text to look through.
        letter: The single letter to count.
    """
    if len(letter) != 1:
        return {"status": "error", "message": "letter must be a single character"}
    count = text.lower().count(letter.lower())
    print(f"[count_letter] {letter!r} in {text!r} = {count}")
    return {"status": "ok", "count": count}


INSTRUCTIONS = {
    "builtin": (
        "You are a careful maths and data helper. For any calculation, counting, date or number-theory question, "
        "write and run Python code and base your answer on the output. Give the final answer in one or two sentences."
    ),
    "calculator": (
        "You are a careful maths helper. NEVER calculate or count in your head. Use the calculate tool for any arithmetic "
        "and the count_letter tool for counting letters, and base your answer on the tool results. If a question needs "
        "something the tools cannot do (such as dates), say so. Give the final answer in one or two sentences."
    ),
    "none": "You are a maths and data helper. Answer the question. Give the final answer in one or two sentences.",
}

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A helper for exact calculations.",
    instruction=INSTRUCTIONS[MODE],
    code_executor=BuiltInCodeExecutor() if MODE == "builtin" else None,
    tools=[calculate, count_letter] if MODE == "calculator" else [],
)
