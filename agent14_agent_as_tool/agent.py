from pydantic import BaseModel, Field
from google.adk.agents import Agent
from google.adk.tools import AgentTool
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent14"  # lets AGENT14_MODEL_PROVIDER override the global choice


def show_tool_call(tool, args, tool_context):
    """Prints every tool call so you can see when the translator is used. Returns None, so the call goes ahead."""
    print(f"[tool call] {tool.name}({args})")
    return None


# The translator's INPUT contract. Without this, an agent used as a tool takes one free-text string, and a
# small model may forget to put the target language in it. With input_schema, the tool declares two
# separate, named arguments, just like a normal function tool.
class TranslationRequest(BaseModel):
    text: str = Field(description="The text to translate.")
    target_language: str = Field(description="The language to translate into, e.g. 'Swedish'.")


# A specialist with one narrow job. It does not talk to the user: the card writer calls it like a function.
translator = Agent(
    name="translator",
    model=get_model(MODEL_KEY),
    description="Translates a short text into a target language.",
    input_schema=TranslationRequest,
    instruction=(
        "You are a translator. The input has the fields text and target_language. "
        "Reply with ONLY the text translated into target_language, nothing else."
    ),
)

# The main agent keeps control of the conversation. It calls the translator as a TOOL, receives the
# result like any tool result, and then writes the final answer itself.
# Compare agent07: there the coordinator TRANSFERRED the conversation to a specialist and was out of the loop.
root_agent = Agent(
    name="card_writer",
    model=get_model(MODEL_KEY),
    description="Writes short greeting-card messages, in any language.",
    instruction=(
        "You write short greeting-card messages (one or two sentences). You cannot translate: only the translator tool can.\n"
        "Step 1, tool: if the user's CURRENT message asks for a language other than English (also in a follow-up such as "
        "'now in French' or 'translate it'), you MUST call the translator tool BEFORE you answer, with the English message "
        "as text and that language as target_language. Do this again in every later message that names a language: "
        "an earlier translation does not count, and writing a translation yourself is wrong.\n"
        "Step 2, answer: show the English message, the translated message returned by the tool, and one short friendly note. "
        "If no language is named, reply with the English message only and do not call any tool."
    ),
    tools=[AgentTool(agent=translator)],
    before_tool_callback=show_tool_call,
)
