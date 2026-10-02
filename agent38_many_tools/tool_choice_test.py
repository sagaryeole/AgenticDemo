"""Ask 24 questions and check which tool the model called FIRST. Same questions, three ways of offering the tools.

Run:   TOOL_MODE=all    uv run python agent38_many_tools/tool_choice_test.py
       TOOL_MODE=vague  uv run python agent38_many_tools/tool_choice_test.py
       TOOL_MODE=routed uv run python agent38_many_tools/tool_choice_test.py
Add MODEL_PROVIDER=local in front for the local model. Every wrong choice is printed under the summary line.
"""
import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent38_many_tools import agent as agent_module
from agent38_many_tools.tools import QUESTIONS


async def first_tool(question: str) -> tuple[str | None, int]:
    """The name of the first tool the model called (None if it called none), and the prompt tokens of its first model call."""
    runner = InMemoryRunner(agent=agent_module.root_agent, app_name="tools")
    session = await runner.session_service.create_session(app_name="tools", user_id="student")
    chosen, tokens = None, 0
    async for event in runner.run_async(user_id="student", session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=question)])):
        if not tokens and event.usage_metadata and event.usage_metadata.prompt_token_count:
            tokens = event.usage_metadata.prompt_token_count
        for call in event.get_function_calls():
            chosen = chosen or call.name
    return chosen, tokens


async def main() -> None:
    right, wrong, token_list = 0, [], []
    for question, expected in QUESTIONS:
        chosen, tokens = await first_tool(question)
        token_list.append(tokens)
        if chosen == expected:
            right += 1
        else:
            wrong.append(f"{question[:55]!r}: called {chosen}, expected {expected}")
    mode = agent_module.TOOL_MODE
    print(f"\nTOOL_MODE={mode}: first tool right {right}/{len(QUESTIONS)}, average prompt tokens of the first call: {sum(token_list) // len(token_list)}, tool calls that failed: {len(agent_module.ERRORS)}")
    for line in wrong:
        print("   wrong:", line)


asyncio.run(main())
