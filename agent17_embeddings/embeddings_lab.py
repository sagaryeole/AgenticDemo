"""Lab 17: embeddings. Turn text into a list of numbers (a vector) so a program can compare MEANING.

Run:   uv run python agent17_embeddings/embeddings_lab.py                           # Gemini embeddings
       EMBEDDING_PROVIDER=local uv run python agent17_embeddings/embeddings_lab.py  # LM Studio embedding model

Needs the same setup as the chat agents: the Gemini settings in .env, or LM Studio running with an embedding model loaded.
"""
import re
from pathlib import Path

import numpy as np

from common.embeddings import embed_texts, embedding_provider

HANDBOOK = Path(__file__).resolve().parent.parent / "data" / "handbook.md"


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """How alike two vectors are, from -1 to 1. Written out and explained in lab 18 (cosine similarity)."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def part1_what_is_a_vector() -> None:
    print("PART 1: a piece of text becomes a vector\n")
    vectors = embed_texts(["The library is closed on Sunday."])
    v = vectors[0]
    print(f"  provider: {embedding_provider()}")
    print(f"  shape of the result: {vectors.shape}  -> 1 text, {v.shape[0]} numbers")
    print(f"  first 6 numbers: {np.round(v[:6], 4)}")
    print(f"  length (norm) of the vector: {np.linalg.norm(v):.3f}")
    print("  The numbers mean nothing one by one. What matters is how close two vectors are.\n")


def part2_meaning_not_words() -> None:
    print("PART 2: close in meaning, not in spelling\n")
    texts = [
        "I deposited my paycheck at the bank.",
        "She opened a savings account.",
        "We had a picnic on the river bank.",
    ]
    vectors = embed_texts(texts)
    names = ["money bank", "savings account", "river bank"]
    print("  similarity matrix (1.0 = identical meaning):")
    print("  " + " " * 18 + "".join(f"{n:>18}" for n in names))
    for i, name in enumerate(names):
        row = "".join(f"{similarity(vectors[i], vectors[j]):>18.3f}" for j in range(len(names)))
        print(f"  {name:<18}{row}")
    print("\n  'bank' appears in two sentences, but the money sentence sits closer to 'savings account'.\n")


def part3_question_vs_answer() -> None:
    print("PART 3: a question and its answer share few words\n")
    question = "How much does it cost when I return a book late?"
    candidates = [
        "Late books cost 25 cents per day, up to a maximum of 5 dollars per book.",
        "The library has four study rooms, each for up to six people.",
        "Printing costs 10 cents per black-and-white page.",
    ]
    q = embed_texts([question], kind="query")[0]
    docs = embed_texts(candidates, kind="document")
    print(f"  question: {question!r}\n")
    for text, d in sorted(zip(candidates, docs), key=lambda p: -similarity(q, p[1])):
        print(f"  {similarity(q, d):.3f}  {text}")
    print("\n  The question never says 'late fee' or '25 cents', yet the right sentence ranks first.\n")


def part4_whole_document() -> None:
    print("PART 4: embed every section of the handbook\n")
    sections = [s.strip() for s in re.split(r"(?m)^(?=## )", HANDBOOK.read_text()) if s.strip().startswith("## ")]
    vectors = embed_texts(sections)
    print(f"  {len(sections)} sections -> matrix of shape {vectors.shape}  (rows = chunks, columns = dimensions)")
    print("  This matrix is the whole 'index'. Searching means comparing a question's vector with each row (lab 18).\n")


def part5_query_vs_document() -> None:
    print("PART 5: tell the model whether the text is a question or a document (Gemini only)\n")
    if embedding_provider() != "gemini":
        print("  Skipped: the local embedding model ignores this setting.\n")
        return
    question = "How much does it cost when I return a book late?"
    docs = embed_texts(["Late books cost 25 cents per day, up to a maximum of 5 dollars per book.",
                        "The library has four study rooms, each for up to six people."], kind="document")
    for kind in ("query", "document"):
        q = embed_texts([question], kind=kind)[0]
        scores = [similarity(q, d) for d in docs]
        print(f"  question embedded as {kind!r:<11} -> right answer {scores[0]:.3f}, unrelated {scores[1]:.3f}, "
              f"gap {scores[0] - scores[1]:.3f}")
    print("\n  Same text, different task setting, different numbers. Use 'query' for questions and 'document' for the text you search.\n")


def part6_never_mix_models() -> None:
    print("PART 6: vectors from different models cannot be compared\n")
    import os
    question = "How much does it cost when I return a book late?"
    answer = "Late books cost 25 cents per day, up to a maximum of 5 dollars per book."
    vectors = {}
    original = os.environ.get("EMBEDDING_PROVIDER")
    try:
        for provider in ("gemini", "local"):
            os.environ["EMBEDDING_PROVIDER"] = provider
            vectors[provider] = (embed_texts([question], kind="query")[0], embed_texts([answer])[0])
    except Exception as exc:  # the other provider may not be set up on this machine
        print(f"  Skipped: could not reach both providers ({type(exc).__name__}).\n")
        return
    finally:
        if original is None:
            os.environ.pop("EMBEDDING_PROVIDER", None)
        else:
            os.environ["EMBEDDING_PROVIDER"] = original
    print(f"  both models give {vectors['gemini'][0].shape[0]} numbers, so the math runs without an error. But:")
    print(f"  gemini question vs gemini answer : {similarity(vectors['gemini'][0], vectors['gemini'][1]):.3f}")
    print(f"  local  question vs local  answer : {similarity(vectors['local'][0], vectors['local'][1]):.3f}")
    print(f"  gemini question vs local  answer : {similarity(vectors['gemini'][0], vectors['local'][1]):.3f}   <- meaningless")
    print("\n  Embed the documents and the question with the SAME model, and re-embed everything if you switch.\n")


if __name__ == "__main__":
    part1_what_is_a_vector()
    part2_meaning_not_words()
    part3_question_vs_answer()
    part4_whole_document()
    part5_query_vs_document()
    part6_never_mix_models()
