import os
from typing import Literal

from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.events import Event
from google.adk.workflow import RetryConfig, Workflow, node
from google.genai import types
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent46"  # lets AGENT46_MODEL_PROVIDER override the global choice

PROBLEM = "A pen costs 3 dollars. How much do 4 pens cost?"   # the right answer is 12

# --- the nodes of the graph ----------------------------------------------------------------------------
# A node is a step. It can be a plain function (no model, always the same), or an agent (one model call).
# Edges say which node runs after which, and a node can pick WHICH edge to follow by returning a "route".

_attempts = {"receive": 0}


@node(retry_config=RetryConfig(max_attempts=4, initial_delay=0.2, jitter=0.0))   # if this node raises an error, ADK runs it again
def receive(node_input, ctx) -> str:
    """Step 1 (a function, no model): take the student's message, remember it, and build the question for the judge."""
    reply = node_input.parts[0].text if hasattr(node_input, "parts") else str(node_input)
    if os.environ.get("FLAKY") == "1":   # pretend that loading the problem fails twice (a flaky service), to show the retry
        _attempts["receive"] += 1
        if _attempts["receive"] % 3 != 0:
            print(f"[receive] attempt {_attempts['receive']}: simulated failure")
            raise ConnectionError("problem service not reachable")
    ctx.state["reply"] = reply
    return f"Problem: {PROBLEM}\nStudent's reply: {reply}"


class Verdict(BaseModel):
    kind: Literal["correct", "arithmetic", "concept", "off_topic"]


# Step 2 (an agent): the only place where the model JUDGES. Its output has a fixed shape (agent06), so the next step can branch on it.
judge = Agent(
    name="judge",
    model=get_model(MODEL_KEY),
    instruction=(
        "You mark a student's reply to a maths problem. The right answer is 12 dollars. Reply with the type of the reply:\n"
        "correct: the answer is 12 (any wording).\n"
        "arithmetic: the student multiplies 3 by 4 (or adds three 4 times) but gets the wrong number.\n"
        "concept: the student uses the wrong operation (for example adds 3 and 4) or does not know what to do.\n"
        "off_topic: the reply has nothing to do with the problem."
    ),
    output_schema=Verdict,
)


def route(node_input, ctx) -> Event:
    """Step 3 (a function): turn the judge's verdict into a ROUTE. The edge with the same name is followed; the others are not."""
    kind = node_input["kind"] if isinstance(node_input, dict) else node_input.kind
    print(f"[route] verdict: {kind}")
    return Event(output=f"Problem: {PROBLEM}\nStudent's reply: {ctx.state['reply']}", route=kind)


# Step 4: one branch per kind of reply. Each has its own small instruction instead of one big prompt that tries to cover every case.
praise = Agent(name="praise", model=get_model(MODEL_KEY),
               instruction="The student's answer is correct. Write ONE short, warm sentence of praise that mentions the answer.")
fix_arithmetic = Agent(name="fix_arithmetic", model=get_model(MODEL_KEY),
                       instruction="The student chose the right method but made an arithmetic mistake. In two short sentences, say the method is right and show the correct multiplication 3 x 4 = 12.")
reteach = Agent(name="reteach", model=get_model(MODEL_KEY),
                instruction="The student used the wrong idea. In two short sentences, explain that 4 pens at 3 dollars each means 4 groups of 3, so we multiply, and give the answer 12.")


def redirect(node_input) -> str:
    """A branch with NO model at all: a fixed answer. Cheap, instant, and impossible to get wrong."""
    return f"That does not look like an answer to the problem. Please try again: {PROBLEM}"


def finish(node_input) -> types.Content:
    """Step 5 (a function): every branch ends here. The message the student sees is this one."""
    text = node_input if isinstance(node_input, str) else str(node_input)
    return types.Content(role="model", parts=[types.Part(text=text.strip() + "\n\n(Homework feedback bot)")])


root_agent = Workflow(
    name="homework_feedback",
    edges=[
        ("START", receive, judge, route, {"correct": praise, "arithmetic": fix_arithmetic, "concept": reteach, "off_topic": redirect}),
        (praise, finish),
        (fix_arithmetic, finish),
        (reteach, finish),
        (redirect, finish),
    ],
)
