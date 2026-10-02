"""Tools that answer questions about grades.csv with real calculation (pandas), for any model.

Nothing here runs text written by the model: a formula is parsed and only numbers, column names and + - * / ( ) are allowed (the same
rule as agent22's calculator). The model chooses which tool and which arguments; pandas does the arithmetic.
"""
import ast
import io
import operator
from pathlib import Path

import pandas as pd
from google.adk.tools import ToolContext
from google.genai import types
from PIL import Image, ImageDraw, ImageFont

CSV = Path(__file__).resolve().parent / "grades.csv"
BASE = pd.read_csv(CSV)

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg}


def _formula_value(node: ast.AST, frame: pd.DataFrame):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in frame.columns and pd.api.types.is_numeric_dtype(frame[node.id]):
        return frame[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_formula_value(node.left, frame), _formula_value(node.right, frame))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_formula_value(node.operand, frame))
    raise ValueError("a formula may only use number columns, numbers, + - * / and parentheses")


def frame(state) -> pd.DataFrame:
    """The table, plus any columns the user asked for earlier in this chat (stored as formulas in session state)."""
    table = BASE.copy()
    for name, formula in (state.get("derived") or {}).items():
        table[name] = _formula_value(ast.parse(formula, mode="eval").body, table)
    return table


def describe_data(tool_context: ToolContext) -> dict:
    """Describes the table: its columns, how many rows, and the first three rows. Call this first."""
    table = frame(tool_context.state)
    return {"columns": list(table.columns), "rows": len(table), "first_rows": table.head(3).to_dict("records")}


def column_stats(column: str, tool_context: ToolContext, group_by: str = "") -> dict:
    """Mean, median, minimum, maximum and count of a number column, optionally for each group (for example each class).

    Args:
        column: The number column, e.g. 'test3'.
        group_by: Optional column to group by, e.g. 'class'. Leave empty for the whole table.
    """
    table = frame(tool_context.state)
    if column not in table.columns:
        return {"error": f"no column {column!r}", "columns": list(table.columns)}
    if group_by:
        grouped = table.groupby(group_by)[column].agg(["mean", "median", "min", "max", "count"]).round(2)
        return {"column": column, "by": group_by, "stats": grouped.reset_index().to_dict("records")}
    s = table[column]
    return {"column": column, "mean": round(float(s.mean()), 2), "median": float(s.median()), "min": float(s.min()), "max": float(s.max()), "count": int(s.count())}


def derive_column(new_name: str, formula: str, tool_context: ToolContext) -> dict:
    """Adds a new number column calculated from existing ones, for example 'improvement' = 'test3 - test1'. It can then be used by the other tools.

    Args:
        new_name: A name for the new column, e.g. 'improvement'.
        formula: Number columns, numbers, + - * / and parentheses only, e.g. 'test3 - test1' or 'test1 + test2 + test3'.
    """
    table = frame(tool_context.state)
    try:
        _formula_value(ast.parse(formula.strip(), mode="eval").body, table)
    except (ValueError, SyntaxError) as error:
        return {"error": str(error)}
    derived = dict(tool_context.state.get("derived") or {})
    derived[new_name] = formula.strip()
    tool_context.state["derived"] = derived
    return {"added": new_name, "formula": formula.strip()}


def top_rows(by: str, tool_context: ToolContext, n: int = 3, ascending: bool = False) -> dict:
    """The n rows (students) with the highest value of a column (or the lowest, if ascending is true).

    Args:
        by: The number column to sort by, e.g. 'test3' or a column made with derive_column.
        n: How many rows to return (default 3).
        ascending: True for the lowest values first.
    """
    table = frame(tool_context.state)
    if by not in table.columns:
        return {"error": f"no column {by!r}", "columns": list(table.columns)}
    return {"rows": table.sort_values(by, ascending=ascending).head(n)[["student", "class", by]].to_dict("records")}


def count_rows(column: str, operator_symbol: str, value: float, tool_context: ToolContext) -> dict:
    """Counts the rows (students) whose column satisfies a comparison, for example test2 < 50.

    Args:
        column: The number column, e.g. 'test2'.
        operator_symbol: One of '<', '<=', '>', '>=', '=='.
        value: The number to compare with.
    """
    table = frame(tool_context.state)
    compare = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge, "==": operator.eq}.get(operator_symbol)
    if column not in table.columns or compare is None:
        return {"error": "unknown column or operator", "columns": list(table.columns)}
    return {"count": int(compare(table[column], value).sum()), "of": len(table)}


async def make_bar_chart(category: str, value: str, title: str, tool_context: ToolContext) -> dict:
    """Draws a bar chart of the AVERAGE of a number column for each value of a category column (for example the average test3 for each class), and saves it as a picture.

    Args:
        category: The column to group by, e.g. 'class'.
        value: The number column to average, e.g. 'test3'.
        title: The chart title, e.g. 'Average test 3 per class'.
    """
    table = frame(tool_context.state)
    if category not in table.columns or value not in table.columns:
        return {"error": "unknown column", "columns": list(table.columns)}
    averages = table.groupby(category)[value].mean().round(1)
    image = Image.new("RGB", (640, 420), "white")
    draw = ImageDraw.Draw(image)
    big, small = ImageFont.load_default(size=22), ImageFont.load_default(size=16)
    draw.text((20, 12), title, fill="black", font=big)
    top = max(1.0, float(averages.max()))
    width = 520 // len(averages)
    for i, (label, number) in enumerate(averages.items()):
        left = 60 + i * width
        height = int(300 * float(number) / top)
        draw.rectangle([left, 360 - height, left + width - 30, 360], fill="steelblue")
        draw.text((left, 360 - height - 22), str(number), fill="black", font=small)
        draw.text((left, 368), str(label), fill="black", font=small)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    filename = "chart.png"
    version = await tool_context.save_artifact(filename, types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/png"))
    print(f"[chart] saved {filename} version {version}: {averages.to_dict()}")
    return {"saved": filename, "version": version, "values": averages.to_dict()}


TOOLS = [describe_data, column_stats, derive_column, top_rows, count_rows, make_bar_chart]
