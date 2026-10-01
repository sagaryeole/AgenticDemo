from google.adk.agents import Agent, LoopAgent
from google.adk.tools import ToolContext
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent10"  # lets AGENT10_MODEL_PROVIDER override the global choice
MAX_WORDS = 6


def check_slogan(slogan: str, names_the_product: bool, tool_context: ToolContext) -> dict:
    """Checks a slogan against all the rules and ends the revision loop if they all pass.

    Args:
        slogan: The slogan text to check.
        names_the_product: Your yes/no judgement: does the slogan name the product or idea?
    """
    # Rules 1 and 3 are checked in code. Models miscount words, code does not.
    words = len(slogan.split())
    has_exclamation = "!" in slogan
    problems = []
    if words > MAX_WORDS:
        problems.append(f"too long: {words} words, the limit is {MAX_WORDS}")
    if has_exclamation:
        problems.append("contains an exclamation mark")
    # Rule 2 needs judgement, so it comes from the model as an argument.
    if not names_the_product:
        problems.append("does not name the product or idea")

    if not problems:
        # escalate=True tells the LoopAgent to stop after this step.
        tool_context.actions.escalate = True
        return {"approved": True, "word_count": words}
    return {"approved": False, "word_count": words, "problems": problems}


# {feedback?} with a question mark means "use it if it exists". On the first
# round the critic has not run yet, so the key is missing and ADK uses an empty value.
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

critic = Agent(
    name="critic",
    model=get_model(MODEL_KEY),
    description="Checks the slogan against the rules and gives feedback if it fails.",
    instruction=(
        "Check this slogan:\n{draft}\n\n"
        "Call check_slogan exactly once with the slogan. For names_the_product, answer true only if "
        "the slogan contains the product or idea the user named (or an obvious part of it).\n"
        "- If the tool says approved is true, reply with the single word: Approved.\n"
        "- Otherwise reply with one short sentence listing the problems the tool returned. "
        "Never count words yourself."
    ),
    tools=[check_slogan],
    output_key="feedback",
)

# Runs writer, then critic, then writer again... until check_slogan approves
# (it sets escalate) or max_iterations is reached, whichever comes first.
root_agent = LoopAgent(
    name="slogan_loop",
    description="Drafts a slogan and revises it until it meets the rules.",
    sub_agents=[writer, critic],
    max_iterations=4,
)
