import os

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent29"  # lets AGENT29_MODEL_PROVIDER override the global choice

# One block of rules per level. The instruction function below picks one, using the level stored in session state.
LEVELS = {
    "kid": "The user is about 10 years old. Use short sentences and everyday words, no technical terms, and an example from daily life.",
    "student": "The user is a secondary-school student. Use correct terms but explain each one, and give a simple example.",
    "expert": "The user is an expert. Be precise and concise, use technical terms freely, and include the key formula or mechanism.",
}

# Few-shot examples: instead of describing the format in words, SHOW one finished answer. Models copy examples closely.
EXAMPLE = """Example of the required format (the topic here is rainbows, at student level):
**In one line:** A rainbow appears when sunlight is split into its colours by raindrops.
**Explanation:** Sunlight contains all colours. When it enters a raindrop it bends (refraction) and each colour bends by a
slightly different amount, so the colours spread out and come back towards you as a band.
**Check yourself:** Why do you only see a rainbow when the sun is behind you?"""


def set_level(level: str, tool_context: ToolContext) -> dict:
    """Changes how simply or deeply explanations are written.

    Args:
        level: One of 'kid', 'student' or 'expert'.
    """
    level = level.strip().lower()
    if level not in LEVELS:
        return {"status": "error", "message": f"level must be one of {sorted(LEVELS)}"}
    tool_context.state["level"] = level
    return {"status": "ok", "level": level}


def set_name(name: str, tool_context: ToolContext) -> dict:
    """Remembers the user's first name, to use when answering.

    Args:
        name: The user's first name.
    """
    tool_context.state["name"] = name.strip()
    return {"status": "ok", "name": name.strip()}


# An INSTRUCTION PROVIDER: a function instead of a fixed string. ADK calls it before EVERY model call, so the instruction
# can change during the conversation. It receives a read-only view of the session, including its state.
def build_instruction(ctx: ReadonlyContext) -> str:
    level = ctx.state.get("level", "student")
    name = ctx.state.get("name")
    text = (
        "You are a friendly study helper that explains one topic at a time.\n"
        f"Current level: {level}. {LEVELS[level]}\n"
        + (f"The user's name is {name}; greet them by name.\n" if name else "")
        + "Step 1, tools: if the user tells you their age, asks for a level, or says the answer is too hard or too easy, FIRST call "
        "set_level (kid, student or expert). If they tell you their name, FIRST call set_name. Saying you changed something "
        "without calling the tool does not change it.\n"
        "Step 2, the answer: explain the topic in exactly three labelled parts: In one line, Explanation, Check yourself.\n"
    )
    # FEW_SHOT=0 leaves the example out, so you can compare a format described in words with a format shown by example.
    if os.environ.get("FEW_SHOT", "1") == "1":
        text += "\n" + EXAMPLE
    if os.environ.get("SHOW_INSTRUCTION") == "1":
        print(f"\n[instruction for this call]\n{text[:400]}...\n")
    else:
        print(f"[instruction] level={level} name={name or '-'}")
    return text


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Explains topics at the user's level.",
    instruction=build_instruction,
    tools=[set_level, set_name],
)
