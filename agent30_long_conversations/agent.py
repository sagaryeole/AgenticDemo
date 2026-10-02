import os

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from common.models import get_model  # global model switch, see common/models.py

MODEL_KEY = "agent30"  # lets AGENT30_MODEL_PROVIDER override the global choice

# CONTEXT_MODE decides how much of the conversation is sent to the model on each call:
#   full     everything, every time (the default behaviour of every agent so far)
#   trim     only the last KEEP_TURNS turns; older turns are simply not sent
#   compact  ADK replaces older turns with a short summary written by the model (EventsCompactionConfig)
MODE = os.environ.get("CONTEXT_MODE", "full").lower()
KEEP_TURNS = 3


def keep_last_turns(callback_context, llm_request):
    """trim mode: drop everything before the last KEEP_TURNS user messages (a 'turn' starts with a user message)."""
    contents = llm_request.contents or []
    starts = [i for i, c in enumerate(contents) if c.role == "user" and any(p.text for p in (c.parts or []))]
    if len(starts) > KEEP_TURNS:
        llm_request.contents = contents[starts[-KEEP_TURNS]:]
    return None


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="A friendly cooking helper for a long chat.",
    instruction=(
        "You are a friendly cooking helper. Keep every answer under 80 words. "
        "Remember personal details the user mentions (name, allergies, pets) and use them when relevant."
    ),
    before_model_callback=keep_last_turns if MODE == "trim" else None,
)


compaction = None
if MODE == "compact":
    # After every 3 new turns, older turns are summarised (keeping 1 turn of overlap with the previous summary).
    compaction = EventsCompactionConfig(
        summarizer=LlmEventSummarizer(llm=get_model(MODEL_KEY)),  # the summarizer is a model call too
        compaction_interval=3,
        overlap_size=1,
    )

# ADK uses `app` when it exists: the agent plus app-wide settings such as compaction.
app = App(name="agent30_long_conversations", root_agent=root_agent, events_compaction_config=compaction)
