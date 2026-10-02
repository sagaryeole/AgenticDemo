"""Play one fixed 14-turn conversation and measure it: prompt tokens per turn, and whether the agent still remembers
facts from the first turn at the end.

Run:   uv run python agent30_long_conversations/long_chat.py --mode full
       uv run python agent30_long_conversations/long_chat.py --mode trim
       uv run python agent30_long_conversations/long_chat.py --mode compact
Add MODEL_PROVIDER=local in front to use the local model (each run then takes a few minutes).
"""
import argparse
import asyncio
import os

parser = argparse.ArgumentParser()
parser.add_argument("--mode", default="full", choices=["full", "trim", "compact"])
args = parser.parse_args()
os.environ["CONTEXT_MODE"] = args.mode  # must be set before the agent module is imported

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from agent30_long_conversations.agent import app  # noqa: E402

TURNS = [
    "Hi! I'm Lina. I'm allergic to peanuts, and my cat is called Pepper.",   # the facts to remember
    "Give me a quick idea for breakfast.",
    "What can I cook with rice and spinach?",
    "How do I make a simple tomato sauce?",
    "Suggest a soup for a cold day.",
    "How long should I boil an egg for a soft yolk?",
    "What is a good vegetarian lunch?",
    "How do I keep fresh herbs from wilting?",
    "Give me an idea for a quick dessert.",
    "What spices go well with carrots?",
    "How do I cook pasta so it doesn't stick?",
    "Suggest a snack for a movie night.",
    "What can I bake with bananas?",
    "Remind me: what is my name, what am I allergic to, and what is my cat called?",   # the memory test
]
FACTS = {"name": "lina", "allergy": "peanut", "cat": "pepper"}


async def main() -> None:
    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(app_name=app.name, user_id="student")
    print(f"model provider: {os.environ.get('MODEL_PROVIDER', 'gemini')}   context mode: {args.mode}\n")
    print(f"{'turn':>4}  {'prompt tokens':>13}  question")
    reply = ""
    for number, text in enumerate(TURNS, start=1):
        prompt_tokens, reply = 0, ""
        message = types.Content(role="user", parts=[types.Part(text=text)])
        async for event in runner.run_async(user_id="student", session_id=session.id, new_message=message):
            if event.usage_metadata and event.usage_metadata.prompt_token_count:
                prompt_tokens = event.usage_metadata.prompt_token_count
            if event.author == "root_agent" and event.content and event.content.parts:
                reply = "".join(p.text or "" for p in event.content.parts) or reply
        print(f"{number:>4}  {prompt_tokens:>13}  {text[:60]}")
    remembered = [fact for fact, word in FACTS.items() if word in reply.lower()]
    print(f"\nlast answer: {reply.strip()[:220]!r}")
    print(f"remembered: {len(remembered)}/3 {remembered}")


if __name__ == "__main__":
    asyncio.run(main())
