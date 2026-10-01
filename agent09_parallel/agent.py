from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent09"  # lets AGENT09_MODEL_PROVIDER override the global choice

# Three independent reviewers. Each reads the same user idea and writes to its
# OWN output_key. Parallel branches must not share a key, or they overwrite each other.
benefits_reviewer = Agent(
    name="benefits_reviewer",
    model=get_model(MODEL_KEY),
    description="Lists the benefits of an idea.",
    instruction="The user describes an idea. List its 3 biggest benefits as short bullet points. Bullets only.",
    output_key="benefits",
)

risks_reviewer = Agent(
    name="risks_reviewer",
    model=get_model(MODEL_KEY),
    description="Lists the risks of an idea.",
    instruction="The user describes an idea. List its 3 biggest risks or downsides as short bullet points. Bullets only.",
    output_key="risks",
)

cost_reviewer = Agent(
    name="cost_reviewer",
    model=get_model(MODEL_KEY),
    description="Estimates the effort and cost of an idea.",
    instruction=(
        "The user describes an idea. In 2-3 sentences, say roughly what time, money and "
        "people it would take. Say clearly that it is a rough guess."
    ),
    output_key="cost",
)

# ParallelAgent starts all three at the same time and finishes when all are done.
review_team = ParallelAgent(
    name="review_team",
    description="Reviews an idea from three angles at once.",
    sub_agents=[benefits_reviewer, risks_reviewer, cost_reviewer],
)

# Runs after the team, so all three state keys exist by now.
verdict_writer = Agent(
    name="verdict_writer",
    model=get_model(MODEL_KEY),
    description="Combines the three reviews into one recommendation.",
    instruction=(
        "Three reviews of an idea are below.\n\n"
        "Benefits:\n{benefits}\n\n"
        "Risks:\n{risks}\n\n"
        "Cost:\n{cost}\n\n"
        "Write a verdict of 3-4 sentences: say go, wait, or no-go, and why. "
        "Use only the information above."
    ),
    output_key="verdict",
)

# Fan out, then fan in: parallel step first, merge step second.
root_agent = SequentialAgent(
    name="idea_review",
    description="Reviews an idea in parallel from three angles, then gives a verdict.",
    sub_agents=[review_team, verdict_writer],
)
