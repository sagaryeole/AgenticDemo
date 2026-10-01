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
class AlertTriage(BaseModel):
    service: str = Field(description="Affected service, e.g. 'payments-api'. 'unknown' if not stated.")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        description="critical = customer-facing outage; high = major degradation; "
        "medium = partial or internal impact; low = cosmetic or no impact."
    )
    category: Literal["database", "network", "capacity", "deployment", "security", "other"]
    summary: str = Field(description="One sentence describing the problem.")
    needs_human: bool = Field(description="True if someone should be paged now.")


root_agent = Agent(
    model=LiteLlm(
        model="openai/qwen3.5-9b",
        api_base=LM_STUDIO_URL,
        api_key="lm-studio",
    ),
    name="root_agent",
    description="Turns a free-text alert into a structured triage record.",
    instruction=(
        "You receive a raw alert or incident description. Classify it into the "
        "required JSON fields. Use only what the alert says; if the service is not "
        "mentioned, set service to 'unknown'. Do not add fields or commentary."
    ),
    # With output_schema ADK disables tools and transfers for this agent,
    # so it can only produce the structured answer.
    output_schema=AlertTriage,
    # Also store the result in session state under this key (see CASES.md case 4).
    output_key="triage",
)
