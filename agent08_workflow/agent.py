from google.adk.agents import Agent, SequentialAgent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent08"  # lets AGENT08_MODEL_PROVIDER override the global choice

# Step 1: explain the topic. output_key saves the reply in session state
# under "explanation" so the next step can read it.
explainer = Agent(
    name="explainer",
    model=get_model(MODEL_KEY),
    description="Explains a topic simply.",
    instruction=(
        "The user gives you a study topic. Explain it in 4-5 short sentences "
        "for a beginner. No headings, no quiz."
    ),
    output_key="explanation",
)

# Step 2: {explanation} is replaced with the value saved by step 1.
quiz_writer = Agent(
    name="quiz_writer",
    model=get_model(MODEL_KEY),
    description="Writes quiz questions from an explanation.",
    instruction=(
        "Write exactly 3 short quiz questions based only on this explanation:\n\n"
        "{explanation}\n\n"
        "Output a numbered list of questions only. No answers."
    ),
    output_key="quiz",
)

# Step 3: reads both earlier results.
answer_key = Agent(
    name="answer_key",
    model=get_model(MODEL_KEY),
    description="Writes the answers for the quiz.",
    instruction=(
        "Explanation:\n{explanation}\n\n"
        "Quiz:\n{quiz}\n\n"
        "Give a one-sentence answer for each numbered question. "
        "Use only the explanation above."
    ),
    output_key="answers",
)

# The workflow agent runs its sub-agents in this fixed order, every time.
# No LLM decides the order, unlike the coordinator in agent07.
root_agent = SequentialAgent(
    name="study_pipeline",
    description="Explain a topic, quiz on it, then give the answers.",
    sub_agents=[explainer, quiz_writer, answer_key],
)
