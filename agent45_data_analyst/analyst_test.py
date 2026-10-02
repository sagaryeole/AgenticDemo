"""Ask 7 questions about grades.csv and check the answers against pandas, for each ANALYSIS_MODE.

Run:   ANALYSIS_MODE=none  uv run python agent45_data_analyst/analyst_test.py
       ANALYSIS_MODE=tools uv run python agent45_data_analyst/analyst_test.py
       ANALYSIS_MODE=code  MODEL_PROVIDER=gemini uv run python agent45_data_analyst/analyst_test.py
Add MODEL_PROVIDER=local in front for the local model. `--show` prints every reply.

How a reply is judged: a number question is right if the reply contains the true number (within 0.06); a name question is right if every true name appears.
"""
import asyncio
import re
import sys

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent45_data_analyst import agent as agent_module
from agent45_data_analyst.tools import BASE

df = BASE.copy()
df["improvement"] = df.test3 - df.test1
df["total"] = df.test1 + df.test2 + df.test3
class_means = df.groupby("class").test3.mean()
best_improver = df.nlargest(1, "improvement").iloc[0]
QUESTIONS = [
    ("What is the average test3 score of all students?", ("number", [df.test3.mean()])),
    ("Which class has the highest average test3 score?", ("names", [class_means.idxmax()])),
    ("Which student improved the most from test1 to test3, and by how many points?", ("names+number", [best_improver.student, best_improver.improvement])),
    ("How many students scored below 50 on test2?", ("number", [(df.test2 < 50).sum()])),
    ("What is the median test2 score?", ("number", [df.test2.median()])),
    ("Who are the three students with the highest total over the three tests?", ("names", list(df.nlargest(3, "total").student))),
    ("What is the average improvement from test1 to test3 for class Oak?", ("number", [df[df["class"] == "Oak"].improvement.mean()])),
]


def is_right(reply: str, kind: str, truth: list) -> bool:
    numbers = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", reply.replace(",", ""))]
    names_ok = lambda items: all(str(t).lower() in reply.lower() for t in items)
    number_ok = lambda value: any(abs(n - float(value)) <= 0.06 for n in numbers)
    if kind == "number":
        return number_ok(truth[0])
    if kind == "names":
        return names_ok(truth)
    return names_ok(truth[:1]) and number_ok(truth[1])


async def ask(question: str) -> str:
    runner = InMemoryRunner(agent=agent_module.root_agent, app_name="analyst")
    session = await runner.session_service.create_session(app_name="analyst", user_id="student")
    reply = ""
    async for event in runner.run_async(user_id="student", session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=question)])):
        if event.is_final_response() and event.content and event.content.parts:
            reply = "".join(p.text or "" for p in event.content.parts if p.text)
    return reply.strip()


async def main() -> None:
    show = "--show" in sys.argv
    right, wrong = 0, []
    for question, (kind, truth) in QUESTIONS:
        reply = await ask(question)
        ok = is_right(reply, kind, truth)
        right += ok
        if not ok:
            wrong.append((question, truth, reply))
        if show:
            print(f"[{'ok ' if ok else 'BAD'}] {question}\n      true: {truth}\n      reply: {' '.join(reply.split())[:200]}")
    print(f"\nANALYSIS_MODE={agent_module.MODE}: {right}/{len(QUESTIONS)} right")
    for question, truth, reply in wrong:
        print(f"   wrong: {question}  (true: {[round(float(t), 2) if not isinstance(t, str) else t for t in truth]})  reply: {' '.join(reply.split())[:110]!r}")


asyncio.run(main())
