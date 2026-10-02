import asyncio
import os
import time
from typing import Any

from google.adk.agents import Agent
from google.adk.models import BaseLlm, Gemini
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from common.models import get_model  # global model switch, see common/models.py

# What can go wrong with a model call, and what this file does about it:
#   error    the service is down, the model name is wrong, the network fails  -> FallbackLlm catches it and uses the backup model
#   too slow the call takes longer than TIMEOUT_SECONDS                       -> FallbackLlm gives up waiting and uses the backup
#   429      too many requests                                                -> retry_options (inside the Gemini object) wait and retry
# Try the failures on purpose with BREAK_PRIMARY (see CASES.md):
#   BREAK_PRIMARY=down   the primary model is pointed at something that does not exist
#   BREAK_PRIMARY=slow   the timeout is 0.3 seconds, which no real model can meet
BREAK_PRIMARY = os.environ.get("BREAK_PRIMARY", "none")
PRIMARY_PROVIDER = os.environ.get("PRIMARY_PROVIDER", "gemini")
BACKUP_PROVIDER = "local" if PRIMARY_PROVIDER == "gemini" else "gemini"
TIMEOUT_SECONDS = 0.3 if BREAK_PRIMARY == "slow" else float(os.environ.get("TIMEOUT_SECONDS", "60"))


def build_primary() -> BaseLlm:
    if BREAK_PRIMARY == "down":
        if PRIMARY_PROVIDER == "gemini":
            return Gemini(model="gemini-no-such-model")                       # Google answers 404: model not found
        return LiteLlm(model="openai/qwen3.5-9b", api_base="http://127.0.0.1:9/v1", api_key="x")  # nothing listens on port 9
    if PRIMARY_PROVIDER == "gemini":
        # only 2 attempts here: the backup is the real safety net, so do not wait a minute on retries first
        return Gemini(model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                      retry_options=types.HttpRetryOptions(attempts=2, initial_delay=2, http_status_codes=[429, 503]))
    return get_model(provider="local")


class FallbackLlm(BaseLlm):
    """A model made of two models. It tries `primary` (within a time limit) and, if that fails or is too slow, `backup`.

    ADK only needs an object with generate_content_async, so any BaseLlm can be wrapped like this. The wrapper collects the
    primary's whole answer before passing it on: it never shows half an answer and then switches models in the middle.
    """
    primary: Any
    backup: Any
    timeout_seconds: float = 60.0
    cooldown_seconds: float = 30.0   # after a failure, do not even try the primary for this long
    skip_primary_until: float = 0.0

    async def generate_content_async(self, llm_request, stream: bool = False):
        try:
            if time.time() < self.skip_primary_until:   # a "circuit breaker": the primary failed a moment ago, so go straight to the backup
                raise RuntimeError("primary skipped during cooldown")
            async with asyncio.timeout(self.timeout_seconds):
                answer = [r async for r in self.primary.generate_content_async(llm_request.model_copy(update={"model": self.primary.model}), stream=False)]
            for response in answer:
                yield response
            return
        except Exception as error:  # includes TimeoutError and every API or network error
            if not isinstance(error, RuntimeError) or "cooldown" not in str(error):
                self.skip_primary_until = time.time() + self.cooldown_seconds
            reason = f"timed out after {self.timeout_seconds}s" if isinstance(error, TimeoutError) else f"{type(error).__name__}: {str(error)[:70]}"
            if "cooldown" in reason:
                print(f"[fallback] primary skipped (it failed less than {self.cooldown_seconds:.0f}s ago); using backup {self.backup.model}")
            else:
                print(f"[fallback] primary {self.primary.model} failed ({reason}); using backup {self.backup.model}")
        async for response in self.backup.generate_content_async(llm_request.model_copy(update={"model": self.backup.model}), stream=False):
            yield response


model = FallbackLlm(
    model="fallback",
    primary=build_primary(),
    backup=get_model(provider=BACKUP_PROVIDER),
    timeout_seconds=TIMEOUT_SECONDS,
)

CITY_FACTS = {"stockholm": "Stockholm is built on 14 islands.", "lisbon": "Lisbon is older than Rome.", "kyoto": "Kyoto has about 1,600 temples."}


async def get_city_fact(city: str) -> dict:
    """Returns one fun fact about a city (Stockholm, Lisbon or Kyoto).

    Args:
        city: The city name.
    """
    if os.environ.get("SLOW_TOOL") == "1":
        await asyncio.sleep(10)   # pretends the service behind this tool is stuck
    return {"fact": CITY_FACTS.get(city.lower(), "No fact known for that city.")}


def with_timeout(function, seconds: float):
    """Wraps an async tool so that it gives up after `seconds` and returns an error the model can explain, instead of freezing the chat."""
    async def wrapper(city: str) -> dict:
        try:
            return await asyncio.wait_for(function(city), timeout=seconds)
        except TimeoutError:
            print(f"[tool timeout] {function.__name__} took longer than {seconds}s")
            return {"error": f"{function.__name__} did not answer within {seconds} seconds. Tell the user it is unavailable right now."}
    wrapper.__name__, wrapper.__doc__ = function.__name__, function.__doc__
    return wrapper


root_agent = Agent(
    model=model,
    name="root_agent",
    description="A city-facts helper that keeps working when its model or its tool fails.",
    instruction="You share fun facts about cities. Call get_city_fact, then answer in one sentence. If the tool reports an error, say so honestly.",
    tools=[with_timeout(get_city_fact, 3.0)],
)
