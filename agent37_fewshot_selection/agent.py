import os

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from common.embeddings import embed_texts
from common.models import get_model  # global model switch, see common/models.py
from agent37_fewshot_selection.examples import LABELS, POOL

MODEL_KEY = "agent37"  # lets AGENT37_MODEL_PROVIDER override the global choice

# Embeddings follow the chat provider unless EMBEDDING_PROVIDER is set explicitly (same rule as agent20).
os.environ.setdefault("EMBEDDING_PROVIDER", os.environ.get("AGENT37_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER", "gemini"))

K = 3  # examples shown per message
_pool_vectors = None


def build_instruction(ctx: ReadonlyContext) -> str:
    """Runs before EVERY model call (like agent29). It looks at the user's latest message, finds the K most similar
    labelled examples in the pool, and writes them into the instruction. A function that returns a string is used
    as is, so the example texts can contain any characters without needing escaping."""
    global _pool_vectors
    message = ""
    if ctx.user_content and ctx.user_content.parts:
        message = "".join(p.text or "" for p in ctx.user_content.parts)
    if _pool_vectors is None:
        _pool_vectors = embed_texts([m for m, _ in POOL], kind="document")
    scores = _pool_vectors @ embed_texts([message], kind="query")[0]
    chosen = [POOL[i] for i in scores.argsort()[::-1][:K]]
    print(f"[examples] for {message[:50]!r}: {[label for _, label in chosen]}")
    shown = "".join(f"Message: {m}\nDepartment: {label}\n\n" for m, label in chosen)
    return (
        f"You route messages from parents to a school department: {', '.join(LABELS)}. "
        "Follow the school's house rules, which you can see in these examples of similar messages:\n\n"
        f"{shown}"
        "Reply with only the department name, then a dash and a few words of reason."
    )


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Routes parent messages to the right school department, using the most similar past examples.",
    instruction=build_instruction,
)
