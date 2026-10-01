from typing import AsyncGenerator

from google.adk.agents import Agent, BaseAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent10"  # lets AGENT10_MODEL_PROVIDER override the global choice
MAX_WORDS = 6


# A plain-Python agent. It has no model: it just checks the rules in code. A workflow step does not
# have to be an LLM. Rules that code can check (word count, a required word) should be checked by
# code, because models miscount, judge leniently, and sometimes skip a tool call.
class SloganChecker(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        slogan = ctx.session.state.get("draft", "")

        # The product is whatever the user typed in their first message.
        product = ""
        for event in ctx.session.events:
            if event.author == "user" and event.content and event.content.parts:
                product = " ".join(p.text for p in event.content.parts if p.text)
                break

        words = len(slogan.split())
        # Rule 2: contain at least one meaningful word (4+ letters) of the product.
        product_words = [w for w in product.lower().replace("-", " ").split() if len(w) >= 4]
        problems = []
        if words > MAX_WORDS:
            problems.append(f"too long: {words} words, the limit is {MAX_WORDS}")
        if "!" in slogan:
            problems.append("contains an exclamation mark")
        if not any(w in slogan.lower() for w in product_words):
            problems.append(f"does not contain any of these words: {', '.join(product_words)}")

        approved = not problems
        feedback = "Approved" if approved else "Rejected: " + "; ".join(problems)

        yield Event(
            author=self.name,
            content=types.Content(role="model", parts=[types.Part(text=f"Approved ({words} words)" if approved else feedback)]),
            # escalate=True tells the LoopAgent to stop after this step.
            # state_delta saves the feedback so the writer can read it next round.
            actions=EventActions(escalate=approved, state_delta={"feedback": feedback}),
        )


# {feedback?} with a question mark means "use it if it exists". On the first
# round the checker has not run yet, so the key is missing and ADK uses an empty value.
writer = Agent(
    name="writer",
    model=get_model(MODEL_KEY),
    description="Writes or revises a slogan.",
    instruction=(
        "You write a slogan for the product or idea the user names.\n"
        "Reviewer feedback on your last draft (empty on the first round): {feedback?}\n\n"
        "If there is feedback, fix exactly what it says. Reply with the slogan only."
    ),
    output_key="draft",
)

checker = SloganChecker(
    name="checker",
    description="Checks the slogan against the rules in code and gives feedback if it fails.",
)

# Runs writer, then checker, then writer again... until the checker escalates
# or max_iterations is reached, whichever comes first.
root_agent = LoopAgent(
    name="slogan_loop",
    description="Drafts a slogan and revises it until it meets the rules.",
    sub_agents=[writer, checker],
    max_iterations=4,
)
