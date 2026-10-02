"""One student asks for their grades 8 times in a row. The policy allows 5 tool calls per 60 seconds per user.

Run:   uv run python agent48_permissions/rate_limit_demo.py
       MODEL_PROVIDER=local uv run python agent48_permissions/rate_limit_demo.py

The counter lives in session state (`recent_calls`, a list of times), written by the same before_tool_callback that checks the role.
"""
import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent48_permissions import agent as agent_module


async def main() -> None:
    agent_module.reset_data()
    # Only for this demo: a model that already knows the answer from the chat may skip the tool, and then there is nothing to limit. So tell it to call the tool every time.
    agent = agent_module.root_agent.clone(update={"instruction": agent_module.root_agent.instruction + " For EVERY request about grades call view_grades again, even if the answer is already in the conversation."})
    runner = InMemoryRunner(agent=agent, app_name="rate")
    session = await runner.session_service.create_session(app_name="rate", user_id="Alma", state={"role": "student", "user_name": "Alma"})
    for i in range(1, 9):
        reply, ran = "", False
        async for event in runner.run_async(user_id="Alma", session_id=session.id,
                                            new_message=types.Content(role="user", parts=[types.Part(text="What are my grades? (request %d)" % i)])):
            for response in event.get_function_responses():
                ran = ran or "scores" in (response.response or {})
            if event.is_final_response() and event.content and event.content.parts:
                reply = "".join(p.text or "" for p in event.content.parts if p.text)
        print(f"request {i}: tool {'RAN    ' if ran else 'BLOCKED'} -> {' '.join(reply.split())[:90]!r}")


asyncio.run(main())
