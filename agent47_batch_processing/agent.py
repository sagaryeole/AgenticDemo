from typing import Literal

from pydantic import BaseModel
from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent47"  # lets AGENT47_MODEL_PROVIDER override the global choice


class Sentiment(BaseModel):
    label: Literal["positive", "negative", "neutral"]


# The worker: it handles ONE review. The batch script (batch.py) runs it many times. A worker agent for batch jobs should be small,
# have no tools and give a fixed output shape (agent06), because nobody is there to answer a follow-up question.
root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Labels one product review as positive, negative or neutral.",
    instruction=(
        "You label one product review. Reply with the label only: positive (the writer is pleased), negative (the writer is unhappy), "
        "or neutral (it only states facts and gives no opinion)."
    ),
    output_schema=Sentiment,
    output_key="result",
)
