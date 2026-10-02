"""ADK's built-in pattern for slow work: LongRunningFunctionTool, then RESUME the conversation when the result arrives.

Run:   uv run python agent33_long_running/resume_demo.py
       MODEL_PROVIDER=local uv run python agent33_long_running/resume_demo.py

Story: a print shop. The agent sends a print job; the shop takes a while. The tool returns "queued" at once and ADK marks the call
as long-running. Later (here: 3 seconds), the shop finishes, and the APP, not the model, sends the final result into the same
session as a function response with the same call id. The agent then continues the conversation with the real result.
"""
import asyncio

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools import LongRunningFunctionTool
from google.genai import types

from common.models import get_model


def send_to_print_shop(document: str, copies: int) -> dict:
    """Sends a document to the print shop. Printing takes a while, so this only returns a ticket.

    Args:
        document: The document name, e.g. 'report.pdf'.
        copies: How many copies to print.
    """
    print(f"   [print shop] received {document} x {copies}, ticket P-17")
    return {"status": "queued", "ticket": "P-17"}


agent = Agent(
    model=get_model("agent33"),
    name="print_assistant",
    instruction=(
        "You help the user print documents with send_to_print_shop. When it returns 'queued', tell the user the ticket number and "
        "that you will let them know when it is ready. When the final result arrives, tell the user where to pick it up."
    ),
    tools=[LongRunningFunctionTool(send_to_print_shop)],
)


async def run_turn(runner, session_id, message: types.Content) -> tuple[str, list[types.FunctionCall]]:
    """Runs one turn. Returns the agent's text and any long-running calls that are still waiting for a result."""
    text, waiting = "", []
    async for event in runner.run_async(user_id="student", session_id=session_id, new_message=message):
        for part in (event.content.parts if event.content and event.content.parts else []):
            if part.text and event.author == agent.name:
                text += part.text
            if part.function_call and event.long_running_tool_ids and part.function_call.id in event.long_running_tool_ids:
                waiting.append(part.function_call)
    return text.strip(), waiting


async def main() -> None:
    runner = InMemoryRunner(agent=agent, app_name="print_demo")
    session = await runner.session_service.create_session(app_name="print_demo", user_id="student")

    print("1. The user asks for printing")
    text, waiting = await run_turn(runner, session.id, types.Content(role="user", parts=[types.Part(text="Please print report.pdf, 20 copies.")]))
    print(f"   agent: {text!r}")
    print(f"   long-running calls still open: {[(c.name, c.id) for c in waiting]}\n")
    if not waiting:
        print("   The model did not call the tool, so there is nothing to resume.")
        return

    print("2. ...time passes. The print shop finishes the job (3 seconds here).")
    await asyncio.sleep(3)

    print("3. The app sends the final result back, using the SAME call id")
    call = waiting[0]
    result = types.Part(function_response=types.FunctionResponse(
        id=call.id, name=call.name, response={"status": "done", "ticket": "P-17", "pickup": "desk 2, ground floor"}))
    text, _ = await run_turn(runner, session.id, types.Content(role="user", parts=[result]))
    print(f"   agent: {text!r}")


if __name__ == "__main__":
    asyncio.run(main())
