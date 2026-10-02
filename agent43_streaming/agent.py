from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent43"  # lets AGENT43_MODEL_PROVIDER override the global choice

# A reply that takes a while to write (about 150 words), so the difference between "wait for all of it" and
# "see it as it is written" is easy to feel.
root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A storyteller: answers with a short story of about 150 words.",
    instruction="You are a storyteller. Whatever the user asks for, answer with a short story of about 150 words, in plain paragraphs.",
)
