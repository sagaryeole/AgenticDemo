"""Streaming: show the reply while it is being written, instead of after.

Run:   uv run python agent43_streaming/stream_demo.py                  (one request, both ways, with timings)
       MODEL_PROVIDER=local uv run python agent43_streaming/stream_demo.py
       uv run python agent43_streaming/stream_demo.py --watch           (prints the story live, word by word)

The model writes the same text either way. What changes is WHEN the user can start reading:
  without streaming  one event arrives when the whole reply is finished
  with streaming     many small "partial" events arrive while it is being written, then one final event with the whole text
"""
import argparse
import asyncio
import time

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent43_streaming.agent import root_agent

PROMPT = "Tell me a story about a robot who learns to bake bread."


async def run_once(streaming: bool, watch: bool = False) -> dict:
    runner = InMemoryRunner(agent=root_agent, app_name="stream_demo")
    session = await runner.session_service.create_session(app_name="stream_demo", user_id="student")
    config = RunConfig(streaming_mode=StreamingMode.SSE if streaming else StreamingMode.NONE)
    start = time.time()
    first_text_at, partials, final_text = None, 0, ""
    async for event in runner.run_async(user_id="student", session_id=session.id, run_config=config,
                                        new_message=types.Content(role="user", parts=[types.Part(text=PROMPT)])):
        text = "".join(p.text or "" for p in event.content.parts) if event.content and event.content.parts else ""
        if not text:
            continue
        if first_text_at is None:
            first_text_at = time.time() - start
        if event.partial:
            partials += 1
            if watch:
                print(text, end="", flush=True)
        else:
            final_text = text
            if watch and not streaming:
                print(text, end="", flush=True)
    return {"first": first_text_at, "total": time.time() - start, "partials": partials, "words": len(final_text.split())}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true", help="print the text as it arrives")
    args = parser.parse_args()
    if args.watch:
        print("streaming, live:\n")
        await run_once(True, watch=True)
        print("\n")
        return
    print(f"{'mode':<16} {'first text after':>17} {'all text after':>15} {'partial events':>15} {'words':>6}")
    for label, streaming in (("no streaming", False), ("streaming", True)):
        r = await run_once(streaming)
        print(f"{label:<16} {r['first']:>15.1f} s {r['total']:>13.1f} s {r['partials']:>15} {r['words']:>6}")


asyncio.run(main())
