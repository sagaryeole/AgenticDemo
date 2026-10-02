"""Lab 19: retrieval logic. The rules around "find the closest chunks": how many, how good, and how to rank.

Run:   uv run python agent19_retrieval/retrieval_lab.py
       EMBEDDING_PROVIDER=local uv run python agent19_retrieval/retrieval_lab.py     # fast, about 2 seconds

Uses the Index class in common/rag.py (labs 16-18 put together). With Gemini it makes about 40 embedding calls and
takes around 4-5 minutes. With the local model it takes a couple of seconds. Embeddings are cached while it runs.
"""
from common.embeddings import embedding_provider
from common.rag import CHUNKERS, Index, load_handbook

# (question, a phrase that the correct chunk must contain). 12 questions the handbook can answer.
ANSWERABLE = [
    ("How much is the late fee for a book?", "25 cents per day"),
    ("How many books can I borrow at once?", "up to 8 books"),
    ("Can I eat in the study room?", "Food is not allowed in the study rooms"),
    ("How do I join the library?", "photo ID"),
    ("What time does the library open on Saturday?", "Saturday from 10:00"),
    ("How much does printing cost?", "10 cents per black-and-white"),
    ("Which form do I need to register for the Coding Club?", "LB-204"),
    ("How do I get the home delivery service?", "LB-310"),
    ("When can I donate books?", "Tuesdays and Thursdays between 10:00"),
    ("Who is the director?", "Helen Park"),
    ("What is the wifi password?", "No password is needed"),
    ("How long can I keep a DVD?", "DVDs and audiobooks can be kept for 7 days"),
]
# 3 questions the handbook says nothing about. The right behaviour is to find NOTHING.
UNANSWERABLE = ["Where can I park my bicycle?", "What is the capital of France?", "Does the library sell coffee?"]
# Short exact terms: a code, a network name, a phone number, a name.
EXACT_TERMS = [("LB-310", "LB-310"), ("What is form LB-204 for?", "LB-204"), ("555-0142", "555-0142"),
               ("Riverside-Guest", "Riverside-Guest"), ("Helen Park", "Helen Park")]


def contains(text: str, phrase: str) -> bool:
    return phrase in " ".join(text.split())


def hit_rate(index: Index, questions, k: int, keyword_weight: float = 0.0) -> int:
    """How many questions have a chunk containing the answer phrase among the top k?"""
    return sum(
        any(contains(h.text, phrase) for h in index.search(q, k=k, keyword_weight=keyword_weight))
        for q, phrase in questions
    )


def part1_top_k(index: Index) -> None:
    print("PART 1: how many chunks to return (top-k), on the 'fixed+overlap' index (small, imperfect chunks)\n")
    print(f"  {'k':>3}  {'answer found in the top k':>27}")
    for k in (1, 2, 3, 5):
        print(f"  {k:>3}  {hit_rate(index, ANSWERABLE, k):>22}/{len(ANSWERABLE)}")
    print("\n  A bigger k catches more answers but hands the model more text to read, including irrelevant text.")
    print("  With very good chunks (try the 'sections' index) k = 1 already finds everything, so k matters most when chunks are weak.\n")


def part2_chunking_matters() -> None:
    print("PART 2: the same questions with different chunking (lab 16), k = 1 and k = 3\n")
    text = load_handbook()
    print(f"  {'strategy':<20} {'chunks':>6} {'best chunk right':>17} {'in top 3':>9}")
    for name, make in CHUNKERS.items():
        index = Index(make(text))
        print(f"  {name:<20} {len(index.chunks):>6} {hit_rate(index, ANSWERABLE, 1):>14}/{len(ANSWERABLE)} "
              f"{hit_rate(index, ANSWERABLE, 3):>6}/{len(ANSWERABLE)}")
    print("\n  Chunks that keep a whole section together found the answer more often than small pieces.\n")


def part3_threshold(index: Index) -> None:
    print("PART 3: a minimum score, so 'no answer' is possible\n")
    best_answerable = [index.search(q, k=1)[0].cosine for q, _ in ANSWERABLE]
    best_unanswerable = [index.search(q, k=1)[0].cosine for q in UNANSWERABLE]
    print(f"  best score for the 12 answerable questions : {min(best_answerable):.2f} to {max(best_answerable):.2f}")
    print(f"  best score for the 3 unanswerable questions: {min(best_unanswerable):.2f} to {max(best_unanswerable):.2f}\n")
    print(f"  {'minimum score':>14} {'answerable kept':>17} {'unanswerable rejected':>23}")
    for threshold in (0.4, 0.5, 0.55, 0.6, 0.65, 0.7):
        kept = sum(s >= threshold for s in best_answerable)
        rejected = sum(s < threshold for s in best_unanswerable)
        print(f"  {threshold:>14.2f} {kept:>14}/{len(ANSWERABLE)} {rejected:>20}/{len(UNANSWERABLE)}")
    print("\n  The ranges overlap, so no single number is perfect: raising it rejects more bad questions but also drops")
    print("  some good ones. Pick the threshold by looking at YOUR data, and recheck it when you change the model.\n")


def part4_keyword_boost() -> None:
    print("PART 4: add exact-word matching to the meaning score (hybrid search), on the 'paragraphs+heading' index\n")
    text = load_handbook()
    index = Index(CHUNKERS["paragraphs+heading"](text))
    print("  final score = cosine + weight x (share of the question's words found exactly in the chunk)\n")
    print(f"  {'weight':>7} {'12 normal questions (best chunk right)':>40} {'5 exact-term queries (best chunk right)':>42}")
    for weight in (0.0, 0.2, 0.5, 1.0):
        normal = hit_rate(index, ANSWERABLE, 1, weight)
        exact = hit_rate(index, EXACT_TERMS, 1, weight)
        print(f"  {weight:>7.1f} {normal:>37}/{len(ANSWERABLE)} {exact:>39}/{len(EXACT_TERMS)}")
    print("\n  Exact words rescue short queries like a network name, which embeddings can blur. But the same words also")
    print("  lift chunks that merely repeat common words, so the boost can cost normal questions. Measure before you use it.\n")


if __name__ == "__main__":
    print(f"Embeddings: {embedding_provider()}\n")
    text = load_handbook()
    sections_index = Index(CHUNKERS["sections"](text))
    part1_top_k(Index(CHUNKERS["fixed+overlap"](text)))
    part2_chunking_matters()
    part3_threshold(sections_index)
    part4_keyword_boost()
