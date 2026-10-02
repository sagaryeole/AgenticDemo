"""Lab 18: cosine similarity. How a program decides which chunk is "closest" to a question.

Run:   uv run python agent18_cosine/cosine_lab.py
       EMBEDDING_PROVIDER=local uv run python agent18_cosine/cosine_lab.py

Parts 1-2 are plain maths and need no model. Parts 3-5 use the embedding model from lab 17.
"""
import math
import re
from pathlib import Path

import numpy as np

HANDBOOK = Path(__file__).resolve().parent.parent / "data" / "handbook.md"


# ---------------------------------------------------------------------------
# The three building blocks, written with plain Python so every step is visible.
# ---------------------------------------------------------------------------

def dot(a: list[float], b: list[float]) -> float:
    """Multiply matching numbers and add them up."""
    return sum(x * y for x, y in zip(a, b))


def norm(a: list[float]) -> float:
    """The length of the vector (Pythagoras)."""
    return math.sqrt(dot(a, a))


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine of the angle between two vectors: 1 = same direction, 0 = unrelated (right angle), -1 = opposite.
    It ignores how long the vectors are and only looks at where they point."""
    return dot(a, b) / (norm(a) * norm(b))


def part1_toy_vectors() -> None:
    print("PART 1: five toy vectors in 2D (no model)\n")
    reference = [1.0, 0.0]
    examples = {
        "same direction, same length": [1.0, 0.0],
        "same direction, 5x longer  ": [5.0, 0.0],
        "a bit different            ": [1.0, 1.0],
        "at a right angle           ": [0.0, 1.0],
        "opposite direction         ": [-1.0, 0.0],
    }
    print(f"  compared with the reference {reference}:\n")
    print(f"  {'vector':<30} {'dot':>6} {'distance':>9} {'cosine':>7} {'angle':>7}")
    for name, v in examples.items():
        distance = math.dist(reference, v)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine(reference, v)))))
        print(f"  {name} {dot(reference, v):>6.2f} {distance:>9.2f} {cosine(reference, v):>7.2f} {angle:>6.0f}°")
    print("\n  The 5x longer vector has a bigger dot product and a bigger distance, but cosine still says 1.00:")
    print("  it points the same way. For text, direction is the meaning and length is mostly noise.\n")


def part2_by_hand_vs_numpy() -> None:
    print("PART 2: the same formula, by hand and with numpy\n")
    a, b = [3.0, 4.0, 1.0], [2.0, 5.0, 0.0]
    print(f"  a = {a}, b = {b}")
    print(f"  dot(a, b)  = 3*2 + 4*5 + 1*0 = {dot(a, b):.1f}")
    print(f"  |a| = {norm(a):.4f}   |b| = {norm(b):.4f}")
    print(f"  cosine by hand : {cosine(a, b):.6f}")
    A, B = np.array(a), np.array(b)
    print(f"  cosine in numpy: {np.dot(A, B) / (np.linalg.norm(A) * np.linalg.norm(B)):.6f}\n")


def load_sections() -> list[str]:
    return [s.strip() for s in re.split(r"(?m)^(?=## )", HANDBOOK.read_text()) if s.strip().startswith("## ")]


def part3_rank_real_chunks() -> None:
    from common.embeddings import embed_texts, embedding_provider

    print(f"PART 3: rank handbook sections for real questions ({embedding_provider()} embeddings)\n")
    sections = load_sections()
    titles = [s.splitlines()[0].lstrip("# ") for s in sections]
    section_vectors = embed_texts(sections, kind="document")          # shape (10, 768)

    questions = [
        "How much is the late fee?",
        "Can I bring my lunch into a study room?",
        "Where can I park my bicycle?",           # the handbook says nothing about this
    ]
    for question in questions:
        q = embed_texts([question], kind="query")[0]                   # shape (768,)
        # Every vector has length 1, so the dot product IS the cosine. One matrix product scores all sections.
        scores = section_vectors @ q
        order = np.argsort(-scores)
        print(f"  question: {question!r}")
        for rank, i in enumerate(order[:3], start=1):
            print(f"    {rank}. {scores[i]:.3f}  {titles[i]}")
        print()
    print("  The first two questions have a clear winner. The bicycle question has no answer in the handbook,")
    print("  but cosine similarity still ranks something first. A ranking never says 'nothing found' by itself (lab 19).\n")


def part4_dot_equals_cosine() -> None:
    from common.embeddings import embed_texts

    print("PART 4: with length-1 vectors, the dot product equals the cosine\n")
    a, b = embed_texts(["late fee for books", "How much do I pay for an overdue book?"])
    print(f"  length of a = {np.linalg.norm(a):.4f}, length of b = {np.linalg.norm(b):.4f}")
    print(f"  dot product : {np.dot(a, b):.6f}")
    print(f"  cosine      : {cosine(list(a), list(b)):.6f}")
    print("  The same number, up to rounding. That is why vector databases often store normalised vectors and just use the dot product.\n")


def part5_distance_agrees() -> None:
    from common.embeddings import embed_texts

    print("PART 5: distance and cosine give the same ranking for length-1 vectors\n")
    sections = load_sections()
    titles = [s.splitlines()[0].lstrip("# ") for s in sections]
    vectors = embed_texts(sections, kind="document")
    q = embed_texts(["How much is the late fee?"], kind="query")[0]
    by_cosine = list(np.argsort(-(vectors @ q)))
    by_distance = list(np.argsort(np.linalg.norm(vectors - q, axis=1)))
    print(f"  top 3 by cosine  : {[titles[i] for i in by_cosine[:3]]}")
    print(f"  top 3 by distance: {[titles[i] for i in by_distance[:3]]}")
    print(f"  same full order? {by_cosine == by_distance}\n")


if __name__ == "__main__":
    part1_toy_vectors()
    part2_by_hand_vs_numpy()
    part3_rank_real_chunks()
    part4_dot_equals_cosine()
    part5_distance_agrees()
