from google.adk.agents import Agent
from .rag_manual import load_runbooks, embed_texts, retrieve

# Embed the corpus once, at import time — not on every tool call
_docs = load_runbooks()
_doc_embeddings = embed_texts([d["text"] for d in _docs])


def get_recent_errors(service: str) -> dict:
    """Return recent error log lines for a service.

    Args:
        service: Service name, e.g. 'payments-api'.
    """
    fake = {"payments-api": ["DB timeout after 30s", "Pool exhausted"]}
    return {"service": service, "errors": fake.get(service, [])}


def search_runbooks(query: str) -> dict:
    """Search internal runbooks for troubleshooting guidance.

    Args:
        query: A description of the symptom or service issue, e.g.
            'database connection timeout on payments service'.
    """
    results = retrieve(query, _docs, _doc_embeddings, top_k=2)
    return {
        "runbooks": [
            {"source": d["id"], "content": d["text"], "score": round(float(s), 3)}
            for d, s in results
        ]
    }


root_agent = Agent(
    name="triage_agent",
    model="gemini-3.8-flash",
    instruction=(
        "You are an SRE assistant. Use get_recent_errors to check for active "
        "errors, and use search_runbooks to find troubleshooting guidance. "
        "Ground your next-step advice in the retrieved runbook content, not "
        "general knowledge. Never invent log data. Clearly separate confirmed "
        "findings (from tool output) from your own speculation — label "
        "speculation explicitly as 'Possible, unconfirmed:' and do not present "
        "it with the same confidence as tool-grounded facts."
    ),
    tools=[get_recent_errors, search_runbooks],
)