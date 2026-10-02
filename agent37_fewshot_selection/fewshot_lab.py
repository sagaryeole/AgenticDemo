"""Lab 37: show the model examples. Which examples matters.

Run:   uv run python agent37_fewshot_selection/fewshot_lab.py
       MODEL_PROVIDER=local EMBEDDING_PROVIDER=local uv run python agent37_fewshot_selection/fewshot_lab.py

Task: route a message from a parent to one of five school departments. The school has house rules (see examples.py) that are
written down NOWHERE except in the labelled examples. Four ways of building the prompt are compared on the same new messages:
  zero-shot   only the five label names
  fixed       the same 3 examples every time (the first three of the pool)
  selected    the 3 pool examples MOST SIMILAR to this message, found with embeddings (labs 17-18)
  random      3 random pool examples (a control: do examples help just by being there?)
"""
import random

from common.embeddings import embed_texts, embedding_provider
from common.llm import ask
from agent37_fewshot_selection.examples import LABELS, POOL, TEST

K = 3


def build_prompt(message: str, examples: list[tuple[str, str]]) -> str:
    shown = "".join(f"Message: {m}\nDepartment: {label}\n\n" for m, label in examples)
    return (f"Route the parent's message to exactly one department: {', '.join(LABELS)}.\n"
            "Reply with only the department name.\n\n" + shown + f"Message: {message}\nDepartment:")


def nearest(message: str, pool_vectors, k: int = K) -> list[tuple[str, str]]:
    """The k pool examples whose meaning is closest to the message (cosine, labs 17-18)."""
    scores = pool_vectors @ embed_texts([message], kind="query")[0]
    return [POOL[i] for i in scores.argsort()[::-1][:k]]


def predicted_label(reply: str) -> str:
    for label in LABELS:
        if label.lower() in reply.lower():
            return label
    return "?"


def run(name: str, pick_examples) -> tuple[int, list[str]]:
    correct, wrong = 0, []
    for message, truth in TEST:
        guess = predicted_label(ask(build_prompt(message, pick_examples(message))).text)
        if guess == truth:
            correct += 1
        else:
            wrong.append(f"{message[:48]!r}: said {guess}, should be {truth}")
    print(f"  {name:<10} {correct:>2}/{len(TEST)} correct")
    return correct, wrong


if __name__ == "__main__":
    print(f"Embeddings: {embedding_provider()}   examples per prompt: {K}   test messages: {len(TEST)}\n")
    pool_vectors = embed_texts([m for m, _ in POOL], kind="document")
    fixed = POOL[:K]
    rng = random.Random(7)
    results = {}
    results["zero-shot"] = run("zero-shot", lambda m: [])
    results["fixed"] = run("fixed", lambda m: fixed)
    results["random"] = run("random", lambda m: rng.sample(POOL, K))
    results["selected"] = run("selected", lambda m: nearest(m, pool_vectors))
    print("\nWhat each method got wrong:")
    for name, (_, wrong) in results.items():
        print(f"  {name}:")
        for line in wrong or ["(nothing)"]:
            print(f"    {line}")
