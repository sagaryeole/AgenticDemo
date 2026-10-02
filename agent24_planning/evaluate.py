"""Run the three puzzles through the agent in one planner mode and count the correct answers.

Run:   uv run python agent24_planning/evaluate.py --mode plan_react --repeats 3
       uv run python agent24_planning/evaluate.py --mode no_thinking --tool off --repeats 3     # Gemini only
Modes: default, no_thinking (Gemini), thinking (Gemini), plan_react. Pick the model with MODEL_PROVIDER=gemini|local.
--tool on|off gives or removes the check_seating tool. --only picks puzzles, e.g. --only seating7 (default: seating7).
Each puzzle runs --repeats times in a fresh session, because models do not give the same answer every time.
"""
import argparse
import asyncio
import os
import re
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--mode", default="default", help="default, no_thinking, thinking or plan_react")
parser.add_argument("--repeats", type=int, default=3)
parser.add_argument("--tool", default="off", choices=["on", "off"], help="give the agent the check_seating tool")
parser.add_argument("--only", default="seating7", help="comma-separated puzzles: seating, seating7, schedule, pets")
args = parser.parse_args()
os.environ["PLANNER_MODE"] = args.mode          # these must be set BEFORE the agent module is imported
os.environ["CHECKER"] = args.tool

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from agent24_planning.agent import root_agent  # noqa: E402
from agent24_planning.puzzles import PUZZLES  # noqa: E402


def normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9:,]", "", text.lower())


async def ask(question: str) -> tuple[str, int, int]:
    """Returns the model's visible reply text and the model's hidden thinking tokens plus visible 'thought' characters."""
    runner = InMemoryRunner(agent=root_agent, app_name="planning")
    session = await runner.session_service.create_session(app_name="planning", user_id="student")
    message = types.Content(role="user", parts=[types.Part(text=question)])
    reply, thought_chars, thinking_tokens = "", 0, 0
    async for event in runner.run_async(user_id="student", session_id=session.id, new_message=message):
        if event.usage_metadata and event.usage_metadata.thoughts_token_count:
            thinking_tokens += event.usage_metadata.thoughts_token_count
        for part in (event.content.parts if event.content and event.content.parts else []):
            if part.text and part.thought:
                thought_chars += len(part.text)
            elif part.text:
                reply += part.text
    return reply, thought_chars, thinking_tokens


async def ask_with_retry(question: str, attempts: int = 4) -> tuple[str, int, int]:
    """Cloud model quotas can say 'try again later' (HTTP 429) when many calls arrive quickly. Wait and retry."""
    for attempt in range(1, attempts + 1):
        try:
            return await ask(question)
        except Exception as exc:  # noqa: BLE001 - report and retry on any API error
            if attempt == attempts:
                raise
            wait = 20 * attempt
            print(f"      (error: {type(exc).__name__} {str(exc)[:60]!r}; waiting {wait}s, retry {attempt}/{attempts - 1})")
            await asyncio.sleep(wait)


async def main() -> None:
    total = correct = 0
    print(f"model provider: {os.environ.get('MODEL_PROVIDER', 'gemini')}   planner mode: {args.mode}   tool: {args.tool}\n")
    wanted = args.only.split(",")
    for name, question, truth in PUZZLES:
        if name not in wanted:
            continue
        for run in range(1, args.repeats + 1):
            started = time.time()
            reply, thoughts, thinking_tokens = await ask_with_retry(question)
            match = re.findall(r"ANSWER:\s*(.+)", reply)
            lines = [l for l in reply.strip().splitlines() if l.strip()]
            # If the model forgot the "ANSWER:" prefix, use its last line, so we measure reasoning and not formatting.
            given = match[-1].strip() if match else (lines[-1].strip() if lines else "(empty reply)")
            note = "" if match else "  [no ANSWER: prefix]"
            if os.environ.get("SHOW_REPLY"):
                print(f"      reply was: {reply.strip()[:300]!r}")
            ok = normalise(given) == normalise(truth)
            total += 1
            correct += ok
            print(f"  {name:<9} run {run}: {'RIGHT' if ok else 'WRONG'}  answer={given!r:<28} hidden_thinking={thinking_tokens:>5} tok  visible_plan={thoughts:>5} chars  {time.time() - started:4.0f}s{note}")
    print(f"\n  correct: {correct} / {total}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
