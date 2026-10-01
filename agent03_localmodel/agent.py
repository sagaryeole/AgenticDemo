import os
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# LM Studio's OpenAI-compatible server (Developer tab -> Start Server)
LM_STUDIO_URL = "http://127.0.0.1:1234/v1"
os.environ["OPENAI_API_BASE"] = LM_STUDIO_URL
os.environ["OPENAI_API_KEY"] = "lm-studio"

root_agent = Agent(
    model=LiteLlm(
        # "openai/<id>" makes LiteLLM use the OpenAI-compatible protocol.
        # <id> must match the model identifier shown in LM Studio exactly.
        model="openai/qwen3.5-9b",
        api_base=LM_STUDIO_URL,
        api_key="lm-studio",
    ),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge.',
)
