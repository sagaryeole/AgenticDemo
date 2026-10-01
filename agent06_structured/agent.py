import os
from typing import Literal
from pydantic import BaseModel, Field
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# LM Studio's OpenAI-compatible server (Developer tab -> Start Server)
LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
os.environ["OPENAI_API_BASE"] = LM_STUDIO_URL
os.environ["OPENAI_API_KEY"] = "lm-studio"


# The output contract. ADK sends this schema to the model and the reply must be
# JSON matching it, so other code can use the result without parsing prose.
class ReviewAnalysis(BaseModel):
    product: str = Field(description="The product the review is about, e.g. 'headphones'. 'unknown' if not stated.")
    sentiment: Literal["positive", "neutral", "negative", "mixed"] = Field(
        description="mixed = clearly both good and bad points; neutral = no strong feeling either way."
    )
    topic: Literal["quality", "price", "delivery", "customer_service", "other"] = Field(
        description="The main thing the review talks about."
    )
    summary: str = Field(description="One sentence summarising the review.")
    needs_reply: bool = Field(description="True if the customer is unhappy or asks a question.")


root_agent = Agent(
    model=LiteLlm(
        model="openai/qwen3.5-9b",
        api_base=LM_STUDIO_URL,
        api_key="lm-studio",
    ),
    name="root_agent",
    description="Turns a free-text customer review into a structured record.",
    instruction=(
        "You receive a customer review. Fill in the required JSON fields. Use only what "
        "the review says; if the product is not mentioned, set product to 'unknown'. "
        "Do not add fields or commentary."
    ),
    # The final reply must match ReviewAnalysis. This agent has no tools, but ADK
    # allows tools together with output_schema: tools run first, and only the
    # final answer is forced into the schema.
    output_schema=ReviewAnalysis,
    # Also store the result in session state under this key (see CASES.md case 5).
    output_key="review",
)
