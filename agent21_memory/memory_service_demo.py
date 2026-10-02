"""ADK's own long-term memory: a MemoryService plus the built-in load_memory tool.

Run:   uv run python agent21_memory/memory_service_demo.py
       MODEL_PROVIDER=local uv run python agent21_memory/memory_service_demo.py
       uv run python agent21_memory/memory_service_demo.py "When is my chem test?"     # your own question for session B

Two separate SESSIONS (two conversations) in one program:
  1. In session A you tell the agent some facts. Then the finished session is added to the memory service.
  2. In session B, a brand-new conversation with no history, the agent finds those facts with load_memory.

InMemoryMemoryService keeps everything in this program's RAM and finds memories by shared KEYWORDS (not meaning), so it is
for learning and testing. It forgets everything when the program ends. Production services (Vertex AI Memory Bank, RAG)
store memories permanently and search by meaning. The agent file next to this one (agent.py) keeps memory in a file instead.
"""
import asyncio
import sys

from google.adk.agents import Agent
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import load_memory
from google.genai import types

from common.models import get_model

APP, USER = "memory_demo", "student"

agent = Agent(
    model=get_model("agent21"),
    name="study_buddy",
    instruction=(
        "You are a study buddy. If the user asks about something they may have told you in an earlier conversation, "
        "call load_memory with a few keywords first, and answer only from what it returns. If it returns nothing "
        "useful, say you do not know."
    ),
    tools=[load_memory],
)


async def say(runner: Runner, session_id: str, text: str) -> str:
    print(f"  you   : {text}")
    reply = ""
    message = types.Content(role="user", parts=[types.Part(text=text)])
    async for event in runner.run_async(user_id=USER, session_id=session_id, new_message=message):
        if event.content and event.content.parts and event.author == agent.name:
            for part in event.content.parts:
                if part.function_call:
                    print(f"  [tool call] {part.function_call.name}({dict(part.function_call.args or {})})")
                elif part.text:
                    reply = part.text
    print(f"  agent : {reply}\n")
    return reply


async def main() -> None:
    sessions, memory = InMemorySessionService(), InMemoryMemoryService()
    runner = Runner(agent=agent, app_name=APP, session_service=sessions, memory_service=memory)

    print("SESSION A: tell the agent some things\n")
    a = await sessions.create_session(app_name=APP, user_id=USER)
    await say(runner, a.id, "My chemistry exam is on 14 November, and I find organic reactions the hardest topic.")

    # The step that makes it long-term: copy the finished session into the memory service.
    a = await sessions.get_session(app_name=APP, user_id=USER, session_id=a.id)
    await memory.add_session_to_memory(a)
    print("  -> session A was added to the memory service\n")

    print("SESSION B: a brand-new conversation (no history, no state)\n")
    b = await sessions.create_session(app_name=APP, user_id=USER)
    question = sys.argv[1] if len(sys.argv) > 1 else "When is my chemistry exam, and which topic did I say was hardest?"
    await say(runner, b.id, question)

    print("SESSION C: ask something that was never said\n")
    c = await sessions.create_session(app_name=APP, user_id=USER)
    await say(runner, c.id, "What is my favourite football team?")


if __name__ == "__main__":
    asyncio.run(main())
