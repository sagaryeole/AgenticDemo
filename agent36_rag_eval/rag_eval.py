"""Lab 36: measure a whole RAG pipeline, step by step, so you know WHICH step is the weak one.

Run:   uv run python agent36_rag_eval/rag_eval.py
       MODEL_PROVIDER=local EMBEDDING_PROVIDER=local uv run python agent36_rag_eval/rag_eval.py
       uv run python agent36_rag_eval/rag_eval.py --show     (also prints every answer)

A RAG answer can go wrong in two places, and they need different fixes:
  RETRIEVAL   did the search bring back the chunk that holds the answer?     (chunking, embeddings, k)
  ANSWER      given the chunks, did the model answer correctly and stay inside them?   (instruction, model)
So each question is scored three ways:
  retrieved   the right chunk is among the top 3, and its rank (for the average reciprocal rank, "MRR")
  correct     the answer contains the key fact (a plain text check, e.g. "25 cents")
  grounded    a second model call judges: "is everything in the answer supported by the passages?"
Three questions have NO answer in the handbook. For them the right behaviour is to say so, not to guess.
This is agent20's job done without ADK, so the same thing can be run 15 times for each of three chunking strategies.
"""
import argparse

from common.embeddings import embedding_provider
from common.llm import ask
from common.rag import CHUNKERS, Index, load_handbook

# (question, phrase that the right chunk contains, key fact the answer must contain)
ANSWERABLE = [
    ("How much is the late fee for a book?", "25 cents per day", "25 cents"),
    ("How many books can I borrow at once?", "up to 8 books", "8"),
    ("Can I eat in the study room?", "Food is not allowed in the study rooms", "not allowed"),
    ("How do I join the library?", "photo ID", "photo id"),
    ("What time does the library open on Saturday?", "Saturday from 10:00", "10:00"),
    ("How much does printing cost?", "10 cents per black-and-white", "10 cents"),
    ("Which form do I need to register for the Coding Club?", "LB-204", "lb-204"),
    ("How do I get the home delivery service?", "LB-310", "lb-310"),
    ("When can I donate books?", "Tuesdays and Thursdays between 10:00", "tuesday"),
    ("Who is the director?", "Helen Park", "helen park"),
    ("How long can I keep a DVD?", "DVDs and audiobooks can be kept for 7 days", "7 days"),
    ("How much does a replacement library card cost?", "a replacement costs 3 dollars", "3 dollars"),
]
UNANSWERABLE = ["Where can I park my bicycle?", "Does the library sell coffee?", "How many floors does the building have?"]
REFUSAL = "couldn't find that"

ANSWER_SYSTEM = (
    "You answer questions about a library using ONLY the passages given. Answer in one or two sentences. "
    "If the passages do not contain the answer, reply exactly: \"I couldn't find that in the handbook.\" Never guess."
)


def answer(question: str, passages: list[str]) -> str:
    listing = "\n\n".join(f"Passage {i + 1}:\n{p}" for i, p in enumerate(passages))
    return ask(f"{listing}\n\nQuestion: {question}", system=ANSWER_SYSTEM).text


def is_grounded(reply: str, passages: list[str]) -> bool:
    """A second model call: is every claim of the answer supported by the passages? (A judge is itself a model, so it can be wrong.)"""
    verdict = ask(
        "Passages:\n" + "\n\n".join(passages) + f"\n\nAnswer to check:\n{reply}\n\n"
        "Is EVERY fact in the answer stated in the passages? Reply with only YES or NO.",
        system="You check answers against source passages.",
    ).text.upper()
    return verdict.startswith("YES")


def evaluate(name: str, chunks: list[str], k: int, show: bool) -> dict:
    index = Index(chunks)
    retrieved = correct = grounded = 0
    reciprocal_ranks = []
    for question, phrase, key_fact in ANSWERABLE:
        hits = index.search(question, k=k)
        texts = [h.text for h in hits]
        rank = next((i for i, t in enumerate(texts, 1) if phrase in " ".join(t.split())), None)
        reciprocal_ranks.append(1 / rank if rank else 0)
        retrieved += rank is not None
        reply = answer(question, texts)
        is_right = key_fact in reply.lower()
        correct += is_right
        grounded += is_grounded(reply, texts)
        if show:
            print(f"    [{'ok ' if is_right else 'BAD'}] retrieved at rank {rank}  {question}\n          -> {reply[:150]}")
    refused = 0
    for question in UNANSWERABLE:
        texts = [h.text for h in index.search(question, k=k)]
        reply = answer(question, texts)
        refused += REFUSAL in reply.lower().replace("’", "'")
        if show:
            print(f"    [{'ok ' if REFUSAL in reply.lower() else 'BAD'}] unanswerable  {question}\n          -> {reply[:150]}")
    n = len(ANSWERABLE)
    return {"name": name, "chunks": len(chunks), "retrieved": retrieved, "mrr": sum(reciprocal_ranks) / n,
            "correct": correct, "grounded": grounded, "refused": refused}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="print every answer")
    parser.add_argument("--k", type=int, default=3, help="how many chunks to give the model")
    args = parser.parse_args()
    print(f"Embeddings: {embedding_provider()}   top-k: {args.k}\n")
    text = load_handbook()
    results = []
    for name in ("fixed+overlap", "paragraphs+heading", "sections"):
        print(f"--- {name}" if args.show else f"running {name} ...")
        results.append(evaluate(name, CHUNKERS[name](text), args.k, args.show))
    n, u = len(ANSWERABLE), len(UNANSWERABLE)
    print(f"\n{'chunking':<20} {'chunks':>6} | {'RETRIEVAL right chunk in top-k':>31} {'MRR':>5} | {'ANSWER correct':>15} {'grounded':>9} | {'refused unanswerable':>21}")
    for r in results:
        print(f"{r['name']:<20} {r['chunks']:>6} | {r['retrieved']:>28}/{n} {r['mrr']:>5.2f} | {r['correct']:>12}/{n} {r['grounded']:>6}/{n} | {r['refused']:>18}/{u}")
