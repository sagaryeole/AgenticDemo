"""Send 12 student replies through the workflow and check that each one took the right branch.

Run:   uv run python agent46_graph_workflow/flow_test.py
       MODEL_PROVIDER=local uv run python agent46_graph_workflow/flow_test.py        (add --show to print every feedback text)

Which branch ran is read from the events: the branch agents (praise, fix_arithmetic, reteach) appear as authors; the off-topic branch has no model, so
its fixed message is recognised by its text.
"""
import asyncio
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent46_graph_workflow.agent import root_agent

REPLIES = [
    ("12 dollars", "praise"), ("The answer is 12.", "praise"), ("4 pens cost 12 dollars because 4 times 3 is 12.", "praise"),
    ("3 x 4 = 11", "fix_arithmetic"), ("4 times 3 is 14 dollars", "fix_arithmetic"), ("3+3+3+3 = 13", "fix_arithmetic"),
    ("I add them: 3 + 4 = 7", "reteach"), ("7 dollars", "reteach"), ("3 divided by 4 is 0.75 dollars", "reteach"),
    ("what is for lunch today?", "redirect"), ("Can I go to the bathroom?", "redirect"), ("I like football.", "redirect"),
]


async def run_one(reply: str) -> tuple[str, str]:
    runner = InMemoryRunner(agent=root_agent, app_name="flow")
    session = await runner.session_service.create_session(app_name="flow", user_id="student")
    authors, final = [], ""
    async for event in runner.run_async(user_id="student", session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=reply)])):
        authors.append(event.author)
        if event.author == "homework_feedback" and event.content and event.content.parts and event.content.parts[0].text:
            final = event.content.parts[0].text
    branch = next((a for a in authors if a in ("praise", "fix_arithmetic", "reteach")), "redirect" if final.startswith("That does not look") else "none")
    return branch, final


async def main() -> None:
    right, wrong = 0, []
    for reply, expected in REPLIES:
        branch, final = await run_one(reply)
        right += branch == expected
        if branch != expected:
            wrong.append(f"{reply!r}: took {branch}, expected {expected}")
        if "--show" in sys.argv:
            print(f"[{'ok ' if branch == expected else 'BAD'}] {reply!r} -> {branch}: {' '.join(final.split())[:150]}")
    print(f"\nright branch: {right}/{len(REPLIES)}")
    for line in wrong:
        print("   wrong:", line)


asyncio.run(main())
