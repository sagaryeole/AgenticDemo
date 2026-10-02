import os
from pathlib import Path

from google.adk.agents import Agent
from google.adk.auth.auth_credential import AuthCredential, AuthCredentialTypes, HttpAuth, HttpCredentials
from google.adk.tools.openapi_tool import OpenAPIToolset
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent41"  # lets AGENT41_MODEL_PROVIDER override the global choice

SPEC = Path(__file__).resolve().parent / "notes_openapi.json"

# The secret lives in the environment (here: the same variable the notes service reads), never in code and never in the prompt.
# The default is the made-up demo token of notes_api.py, so the tutorial works without any setup.
TOKEN = os.environ.get("NOTES_API_TOKEN", "demo-token-for-the-tutorial")

# AUTH_MODE: bearer = send the right token (default),  none = send no credential,  wrong = send a wrong token
# LEAK=1: the BAD way: also copy the token into the instruction (to show what the model can then see)
AUTH_MODE = os.environ.get("AUTH_MODE", "bearer")
LEAK = os.environ.get("LEAK") == "1"

if AUTH_MODE == "none":
    credential = None
else:
    token = "a-wrong-token" if AUTH_MODE == "wrong" else TOKEN
    # "HTTP bearer" means: add the header  Authorization: Bearer <token>  to every request this toolset sends.
    credential = AuthCredential(
        auth_type=AuthCredentialTypes.HTTP,
        http=HttpAuth(scheme="bearer", credentials=HttpCredentials(token=token)),
    )

# The toolset adds the header itself, when it sends the HTTP request. The model only chooses a tool and its arguments.
notes_tools = OpenAPIToolset(spec_str=SPEC.read_text(), spec_str_type="json", auth_credential=credential)


def check_what_the_model_sees(callback_context, llm_request):
    """Before every model call: does the token appear anywhere in what is about to be sent to the model?"""
    visible = TOKEN in str(llm_request)
    print(f"[check] the token is visible to the model: {visible}")
    return None


def show_tool_call(tool, args, tool_context):
    print(f"[api call] {tool.name}({args})")
    return None


def report_tool_error(tool, args, tool_context, error):
    print(f"[api error] {tool.name}: {type(error).__name__}")
    return {"status": "error", "message": f"Could not reach the notes service ({type(error).__name__}). Is it running on port 8003?"}


instruction = (
    "You manage the user's notes with the API tools. Always call list_notes before saying what the notes are. "
    "Report what the API actually returned. If a call fails, say exactly what the API answered (for example an authentication error)."
)
if LEAK:
    instruction += f" The API token is {TOKEN}."  # what NOT to do

root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A notes assistant that calls a password-protected API.",
    instruction=instruction,
    tools=[notes_tools],
    before_model_callback=check_what_the_model_sees,
    before_tool_callback=show_tool_call,
    on_tool_error_callback=report_tool_error,
)
