from google.adk.agents import Agent
from google.adk.tools import AgentTool
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent42"  # lets AGENT42_MODEL_PROVIDER override the global choice

# A small fact sheet: the checker's only source of truth. (Made-up lookups would be wrong; real facts, kept short.)
FACTS = {
    "moon": "Average distance from Earth: 384,400 km. Diameter: 3,474 km. One orbit around Earth: 27.3 days. Gravity: about one sixth of Earth's. Has no atmosphere.",
    "mars": "Average distance from the Sun: 228 million km. Diameter: 6,779 km. One year: 687 Earth days. Has two small moons: Phobos and Deimos.",
    "octopus": "Has three hearts and blue blood. Has eight arms. Most live 1 to 5 years. Has no skeleton.",
}


def lookup_fact(topic: str) -> dict:
    """Looks up verified facts about a topic (moon, mars or octopus).

    Args:
        topic: The topic name, one word, e.g. 'moon'.
    """
    return {"facts": FACTS.get(topic.lower().strip(), "No facts stored for this topic.")}


def show_call(tool, args, tool_context):
    """Prints each call the supervisor makes, so you can watch the order of work."""
    preview = " ".join(str(next(iter(args.values()), "")).split())[:90]
    print(f"[supervisor -> {tool.name}] {preview}")
    return None


# Three specialists. None of them talks to the user: the supervisor calls them like functions (agent14) and reads their results.
planner = Agent(
    name="planner",
    model=get_model(MODEL_KEY),
    description="Turns a writing request into a plan of three short points.",
    instruction="You plan short texts. Reply with exactly three numbered points saying what the text should cover. No other words.",
)

writer = Agent(
    name="writer",
    model=get_model(MODEL_KEY),
    description="Writes or rewrites a short text from a plan, and from a list of problems to fix when given one.",
    instruction=(
        "You write short, clear texts for students (about 4 sentences). The input contains a plan or a task, and sometimes a draft with "
        "a list of PROBLEMS. If there are problems, rewrite the draft and fix every one of them, using exactly the corrected facts you were given. "
        "Reply with the text only."
    ),
)

fact_checker = Agent(
    name="fact_checker",
    model=get_model(MODEL_KEY),
    description="Checks every factual claim in a draft against the fact sheet and reports problems.",
    instruction=(
        "You check a draft text. Call lookup_fact with the topic (one word), then compare EVERY number and claim in the draft with the facts. "
        "If everything is correct, reply with exactly: OK. "
        "Otherwise reply starting with 'PROBLEMS:' and list each wrong claim with the correct fact from the fact sheet. Do not rewrite the draft."
    ),
    tools=[lookup_fact],
)

root_agent = Agent(
    name="supervisor",
    model=get_model(MODEL_KEY),
    description="Manages a planner, a writer and a fact checker to produce a short, checked text.",
    instruction=(
        "You are a supervisor. You do not write or check anything yourself: you call your three tools and pass results between them.\n"
        "Work in this order:\n"
        "1. Call planner with the user's request.\n"
        "2. Call writer with the plan AND everything the user asked to include, word for word.\n"
        "3. Call fact_checker with the draft.\n"
        "4. If fact_checker replies 'OK', stop. If it replies 'PROBLEMS:', call writer again with the full draft plus the full list of problems, "
        "then call fact_checker on the new draft. Repeat, but at most 2 rewrites.\n"
        "Finish with the final text. If the fact checker corrected something the USER asked to include, add one sentence saying what was wrong and what the correct fact is. "
        "Last line: 'Checked: <OK or still has problems> after <n> rewrite(s).'"
    ),
    tools=[AgentTool(agent=planner), AgentTool(agent=writer), AgentTool(agent=fact_checker)],
    before_tool_callback=show_call,
)
