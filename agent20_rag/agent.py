import os

from google.adk.agents import Agent
from common.models import get_model  # global model switch, see common/models.py (also loads the root .env)
from common.rag import Index, load_handbook, sections

MODEL_KEY = "agent20"  # lets AGENT20_MODEL_PROVIDER override the global choice

# Embeddings follow the chat provider unless EMBEDDING_PROVIDER is set explicitly, so
# MODEL_PROVIDER=local gives a fully local agent (chat and search both in LM Studio).
os.environ.setdefault("EMBEDDING_PROVIDER", os.environ.get("AGENT20_MODEL_PROVIDER") or os.environ.get("MODEL_PROVIDER", "gemini"))

# Settings carried over from lab 19 (see agent19_retrieval/CASES.md, case 8).
TOP_K = 3
# Just below the lowest score of a good answer in lab 19 (0.51 Gemini, 0.48 local). It drops clearly irrelevant
# chunks, but cannot catch every unanswerable question, so the instruction also tells the model to check.
MIN_SCORE = {"gemini": 0.50, "local": 0.45}

_index: Index | None = None


def _get_index() -> Index:
    """Build the index on the first search (chunks -> embeddings), then reuse it."""
    global _index
    if _index is None:
        _index = Index(sections(load_handbook()))
    return _index


def search_handbook(question: str) -> dict:
    """Searches the Riverside Community Library Handbook and returns the most relevant passages.

    Args:
        question: What the user wants to know, as a short question or phrase, e.g. 'late fee for books'.
    """
    provider = os.environ["EMBEDDING_PROVIDER"].lower()
    hits = _get_index().search(question, k=TOP_K, min_score=MIN_SCORE.get(provider, 0.5))
    print(f"[search_handbook] {question!r} -> {[(h.text.splitlines()[0].lstrip('# '), round(h.score, 2)) for h in hits]}")
    if not hits:
        return {"passages": [], "note": "Nothing relevant was found in the handbook."}
    return {
        "passages": [
            {"section": h.text.splitlines()[0].lstrip("# "), "text": h.text, "score": round(h.score, 2)}
            for h in hits
        ]
    }


root_agent = Agent(
    model=get_model(MODEL_KEY),
    name="root_agent",
    description="Answers questions about the Riverside Community Library from its handbook.",
    instruction=(
        "You answer questions about the Riverside Community Library. For EVERY new question, call "
        "search_handbook first, even if you answered something similar earlier or earlier searches found nothing. "
        "Never reuse a previous answer without searching again. "
        "Answer ONLY from the passages it returns, in one to three sentences, and name "
        "the section you used in square brackets, like [Borrowing rules]. "
        "If no passages come back, or the passages do not actually contain the answer, say exactly: "
        "\"I couldn't find that in the handbook.\" Never answer from your own knowledge, and never guess."
    ),
    tools=[search_handbook],
)
