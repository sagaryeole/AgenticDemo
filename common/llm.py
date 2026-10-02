"""Ask a model ONE question directly, with no agent, no tools and no session. Same Gemini / local switch as common/models.py.

Labs (reranking, evaluation, few-shot, cost) call a model dozens of times and only need "prompt in, text out",
plus the token counts and the time. An agent would add nothing but overhead there.

    reply = ask("What is 2 + 2?")
    print(reply.text, reply.prompt_tokens, reply.output_tokens, reply.seconds)

Env vars: MODEL_PROVIDER (gemini / local), GEMINI_MODEL, LOCAL_MODEL_ID, LOCAL_API_BASE (the same ones as get_model).
"""
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


@dataclass
class Reply:
    text: str
    prompt_tokens: int
    output_tokens: int
    seconds: float
    cached_tokens: int = 0   # prompt tokens Gemini served from its cache (agent39)


# Always sent, even when the caller gives none. In testing, the LOCAL model (qwen3.5-9b) answered an open question such as "Explain why the sky
# is blue." with "CLARIFICATION NEEDED: ..." when no system instruction was sent, and normally when any was sent. Gemini answered normally either way.
# (Agents are not affected: they always have an instruction.) So every direct call carries a minimal one, for both providers.
DEFAULT_SYSTEM = "You are a helpful assistant."


def provider(name: str | None = None) -> str:
    """The provider for this call: an explicit name, else AGENTNN_MODEL_PROVIDER, else MODEL_PROVIDER."""
    return (name or os.environ.get("MODEL_PROVIDER", "gemini")).lower()


def ask(prompt: str, system: str | None = None, model: str | None = None, max_tokens: int | None = None,
        temperature: float = 0.0, provider_name: str | None = None) -> Reply:
    """Send one prompt and return the reply.

    Args:
        prompt: the user message.
        system: instructions placed before it (default: a one-line 'helpful assistant', see DEFAULT_SYSTEM).
        model: a model name that replaces GEMINI_MODEL / LOCAL_MODEL_ID for this call (used to compare models).
        max_tokens: cap on the reply length.
        temperature: 0 means "as repeatable as possible".
        provider_name: "gemini" or "local"; default follows MODEL_PROVIDER.
    """
    which = provider(provider_name)
    system = system or DEFAULT_SYSTEM
    start = time.time()
    if which == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=6, initial_delay=5, max_delay=60, http_status_codes=[429, 503])))
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature, max_output_tokens=max_tokens)
        result = client.models.generate_content(
            model=model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt, config=config)
        usage = result.usage_metadata
        return Reply(
            text=(result.text or "").strip(),
            prompt_tokens=(usage.prompt_token_count or 0) if usage else 0,
            # Gemini's hidden "thinking" tokens are billed like output, so they are counted here too
            output_tokens=((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0,
            seconds=time.time() - start,
            cached_tokens=(usage.cached_content_token_count or 0) if usage else 0,
        )

    if which == "local":
        base = os.environ.get("LOCAL_API_BASE", "http://127.0.0.1:1234/v1").rstrip("/")
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = {"model": model or os.environ.get("LOCAL_MODEL_ID", "qwen3.5-9b"), "messages": messages, "temperature": temperature}
        if max_tokens:
            body["max_tokens"] = max_tokens
        response = httpx.post(f"{base}/chat/completions", json=body, timeout=300)
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage", {})
        return Reply(
            text=(data["choices"][0]["message"].get("content") or "").strip(),
            prompt_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            seconds=time.time() - start,
        )

    raise ValueError(f"MODEL_PROVIDER must be 'gemini' or 'local', got {which!r}")
