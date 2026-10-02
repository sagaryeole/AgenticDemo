"""Send an image to the agent directly in code, and see what it costs in tokens.

Run:   uv run python agent28_multimodal/ask_with_image.py
       MODEL_PROVIDER=local uv run python agent28_multimodal/ask_with_image.py

This is how an app (a website, a phone app) would send a photo: the user message is a list of parts, and the image is
one of them. It asks the same question twice, without and with the image, and prints the prompt tokens of each call.
"""
import asyncio
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent28_multimodal.agent import root_agent

IMAGE = Path(__file__).resolve().parent / "images" / "chart.png"
QUESTION = "Which day had the fewest visitors in this chart?"


async def ask(parts: list[types.Part]) -> tuple[str, int]:
    runner = InMemoryRunner(agent=root_agent, app_name="image_demo")
    session = await runner.session_service.create_session(app_name="image_demo", user_id="student")
    reply, prompt_tokens = "", 0
    async for event in runner.run_async(user_id="student", session_id=session.id,
                                        new_message=types.Content(role="user", parts=parts)):
        if event.usage_metadata and event.usage_metadata.prompt_token_count:
            prompt_tokens = event.usage_metadata.prompt_token_count
        for part in (event.content.parts if event.content and event.content.parts else []):
            if part.text:
                reply += part.text
    return reply.strip(), prompt_tokens


async def main() -> None:
    text_only = [types.Part(text=QUESTION)]
    with_image = [types.Part(text=QUESTION), types.Part.from_bytes(data=IMAGE.read_bytes(), mime_type="image/png")]

    for label, parts in [("text only ", text_only), ("with image", with_image)]:
        reply, tokens = await ask(parts)
        print(f"{label}: {tokens:>5} prompt tokens -> ...{reply[-140:]!r}")


if __name__ == "__main__":
    asyncio.run(main())
