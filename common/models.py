"""Global model switch for the demo agents (agent07 onwards).

Set MODEL_PROVIDER in aiops-poc/.env to choose for every agent that uses
get_model(). Set <AGENT_NAME>_MODEL_PROVIDER to override a single agent.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm

# Root .env holds the global choice. override=False keeps real environment
# variables (and each agent folder's own .env) in charge when they are set.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

PROVIDERS = ("local", "gemini")


def get_model(agent_name: str | None = None):
    """Return the model for an agent, based on environment variables.

    Args:
        agent_name: e.g. "agent07". If AGENT07_MODEL_PROVIDER is set it wins
            over the global MODEL_PROVIDER.
    """
    provider = None
    if agent_name:
        provider = os.environ.get(f"{agent_name.upper()}_MODEL_PROVIDER")
    provider = (provider or os.environ.get("MODEL_PROVIDER", "gemini")).lower()

    if provider == "gemini":
        # ADK treats a plain string as a native Gemini model name.
        return os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    if provider == "local":
        base = os.environ.get("LOCAL_API_BASE", "http://127.0.0.1:1234/v1")
        # "openai/<id>" = OpenAI-compatible protocol; <id> must match LM Studio.
        return LiteLlm(
            model=f"openai/{os.environ.get('LOCAL_MODEL_ID', 'qwen3.5-9b')}",
            api_base=base,
            api_key=os.environ.get("LOCAL_API_KEY", "lm-studio"),
        )

    raise ValueError(f"MODEL_PROVIDER must be one of {PROVIDERS}, got {provider!r}")
