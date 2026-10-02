"""Lab 35: three ways to find the right chunk, and a fourth step that re-reads the best few.

Run:   uv run python agent35_hybrid_rerank/rerank_lab.py
       MODEL_PROVIDER=local EMBEDDING_PROVIDER=local uv run python agent35_hybrid_rerank/rerank_lab.py

Same library handbook as labs 16-20, chunked as 'paragraphs+heading'. Each question has a phrase that the right chunk contains.
  1. vectors   meaning search (labs 17-19)
  2. BM25      keyword search: counts the question's exact words, rare words count more (no model at all)
  3. hybrid    both rankings merged with reciprocal rank fusion
  4. rerank    hybrid's top 5, re-read by a language model that scores each one against the question

The reranking step makes one model call per question, so with Gemini the whole lab takes a few minutes.
"""
import time

from common.embeddings import embed_texts, embedding_provider
from common.rag import BM25, CHUNKERS, Index, llm_rerank, load_handbook, ranking, reciprocal_rank_fusion

# Questions that use DIFFERENT words from the handbook (a sandwich is "food", a booth is a "study room"). Meaning search should win.
PARAPHRASED = [
    ("Am I allowed to bring a sandwich into the quiet booths?", "Food is not allowed in the study rooms"),
    ("What happens if I return a novel after the due date?", "Late books cost 25 cents per day"),
    ("What do I do if my membership card goes missing?", "a replacement costs 3 dollars"),
    ("Is there somewhere for a group to work together quietly?", "four study rooms"),
    ("Can someone in a wheelchair get into the building?", "step-free entrance"),
    ("What are the opening hours at the weekend?", "Saturday from 10:00"),
    ("How can I make my loan last longer?", "renew an item twice"),
    ("How much do photocopies in colour cost?", "50 cents per colour page"),
]
# Short exact terms: a form code, a phone number, a network name, a person. Keyword search should win.
EXACT = [
    ("LB-310", "LB-310"),
    ("form LB-204", "LB-204"),
    ("555-0142", "555-0142"),
    ("Riverside-Guest", "Riverside-Guest"),
    ("Helen Park", "Helen Park"),
    ("Which form is for the Coding Club?", "LB-204"),
]


def contains(text: str, phrase: str) -> bool:
    return phrase in " ".join(text.split())


def position_of_answer(order: list[int], chunks: list[str], phrase: str) -> int | None:
    """1-based position of the first chunk that contains the answer phrase in this ordering, or None."""
    for position, chunk_number in enumerate(order, start=1):
        if contains(chunks[chunk_number], phrase):
            return position
    return None


def orderings(question: str, index: Index, bm25: BM25) -> dict[str, list[int]]:
    """The chunk order (best first) that each method gives for a question."""
    vector_order = ranking(list(index.vectors @ embed_texts([question], kind="query")[0]))
    keyword_order = ranking(bm25.scores(question))
    hybrid_order = reciprocal_rank_fusion([vector_order, keyword_order])
    top5 = hybrid_order[:5]
    reranked = [top5[i] for i in llm_rerank(question, [index.chunks[n] for n in top5])]
    return {"vectors": vector_order, "BM25": keyword_order, "hybrid": hybrid_order, "hybrid + rerank": reranked + hybrid_order[5:]}


def score_table(title: str, questions, index: Index, bm25: BM25, cache: dict) -> None:
    print(f"{title}  ({len(questions)} questions)\n")
    print(f"  {'method':<18} {'best chunk right':>17} {'right chunk in top 3':>21} {'average rank of the right chunk':>33}")
    methods = ["vectors", "BM25", "hybrid", "hybrid + rerank"]
    positions = {m: [] for m in methods}
    for question, phrase in questions:
        if question not in cache:
            cache[question] = orderings(question, index, bm25)
        for method in methods:
            positions[method].append(position_of_answer(cache[question][method], index.chunks, phrase))
    for method in methods:
        found = positions[method]
        first = sum(p == 1 for p in found)
        top3 = sum(p is not None and p <= 3 for p in found)
        average = sum(p if p else len(index.chunks) for p in found) / len(found)
        print(f"  {method:<18} {first:>14}/{len(questions)} {top3:>18}/{len(questions)} {average:>33.2f}")
    print()


def part3_one_example(index: Index, bm25: BM25, cache: dict) -> None:
    """Show the question where the four methods disagree the most, so you can see what each step changes."""
    methods = ("vectors", "BM25", "hybrid", "hybrid + rerank")
    phrases = dict(PARAPHRASED + EXACT)

    def spread(question: str) -> int:
        """How many different positions the methods give the right chunk (1 = they all agree)."""
        return len({position_of_answer(cache[question][m], index.chunks, phrases[question]) for m in methods})

    question = max(phrases, key=spread)
    print(f"PART 3: the question where the methods disagree most:  {question!r}\n")
    for method in methods:
        order = cache[question][method]
        right = position_of_answer(order, index.chunks, phrases[question])
        print(f"  {method:<16} right chunk at position {right};  top chunk starts: {index.chunks[order[0]][:60]!r}")
    print()


if __name__ == "__main__":
    print(f"Embeddings: {embedding_provider()}\n")
    chunks = CHUNKERS["paragraphs+heading"](load_handbook())
    index, bm25 = Index(chunks), BM25(chunks)
    print(f"{len(chunks)} chunks\n")
    cache: dict = {}
    start = time.time()
    print("PART 1: questions in different words from the handbook\n")
    score_table("paraphrased", PARAPHRASED, index, bm25, cache)
    print("PART 2: exact terms\n")
    score_table("exact terms", EXACT, index, bm25, cache)
    part3_one_example(index, bm25, cache)
    print(f"(whole lab: {time.time() - start:.0f} s; the rerank step made {len(cache)} model calls)")
