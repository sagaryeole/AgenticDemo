"""Lab 49: a big model teaches a small one. How much of the big model's skill can the small one keep?

Run:   EMBEDDING_PROVIDER=local uv run python agent49_distillation/distill_lab.py
       uv run python agent49_distillation/distill_lab.py --refresh        (ask the teacher again instead of using teacher_labels.json)

The idea ("distillation by labelling"):
  1. TEACHER   a large, expensive model (gemini-2.5-pro) is given the school's written house rules and labels 60 new messages.
  2. STUDENTS  small, cheap models (the local model, and gemini-2.5-flash-lite) are NOT given the rules. Each gets only a few labelled examples
               (the 3 most similar, picked with embeddings, as in agent37) taken from the teacher's labels.
  3. TEST      the same 24 messages as agent37, which none of the models has seen. Students are scored on them.
Rows compare what the student is given: nothing / the rules in words (what the teacher had) / examples labelled by the teacher /
examples labelled by a human (the true labels, an upper bound) / agent37's 36 hand-written examples.
"""
import argparse
import json
from pathlib import Path

from common.embeddings import embed_texts, embedding_provider
from common.llm import ask
from agent37_fewshot_selection.examples import LABELS, POOL, TEST
from agent37_fewshot_selection.fewshot_lab import predicted_label
from agent49_distillation.messages import HOUSE_RULES, UNLABELED

TEACHER = "gemini-2.5-pro"
STUDENTS = [("local qwen3.5-9b", "local", None), ("gemini-2.5-flash-lite", "gemini", "gemini-2.5-flash-lite")]
CACHE = Path(__file__).resolve().parent / "teacher_labels.json"
K = 3


def teacher_labels(refresh: bool) -> dict:
    """Label the 60 messages with the teacher, once; the answers (and what they cost) are saved in teacher_labels.json."""
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text())
    labels, input_tokens, output_tokens, seconds = {}, 0, 0, 0.0
    for message, _ in UNLABELED:
        reply = ask(f"Route this parent's message to exactly one department: {', '.join(LABELS)}.\n{HOUSE_RULES}\nReply with only the department name.\n\nMessage: {message}\nDepartment:",
                    model=TEACHER, provider_name="gemini")
        labels[message] = predicted_label(reply.text)
        input_tokens += reply.prompt_tokens
        output_tokens += reply.output_tokens
        seconds += reply.seconds
    data = {"model": TEACHER, "labels": labels, "input_tokens": input_tokens, "output_tokens": output_tokens, "seconds": round(seconds, 1)}
    CACHE.write_text(json.dumps(data, indent=1))
    return data


def prompt(message: str, examples: list[tuple[str, str]], with_rules: bool) -> str:
    shown = "".join(f"Message: {m}\nDepartment: {label}\n\n" for m, label in examples)
    rules = HOUSE_RULES + "\n" if with_rules else ""
    return (f"Route the parent's message to exactly one department: {', '.join(LABELS)}.\n{rules}Reply with only the department name.\n\n{shown}Message: {message}\nDepartment:")


def nearest(message: str, pool: list[tuple[str, str]], vectors) -> list[tuple[str, str]]:
    scores = vectors @ embed_texts([message], kind="query")[0]
    return [pool[i] for i in scores.argsort()[::-1][:K]]


def score(student, pick) -> tuple[int, int]:
    """Right answers on the 24 test messages, and the average prompt tokens per message."""
    _, provider, model = student
    right = tokens = 0
    for message, truth in TEST:
        examples, with_rules = pick(message)
        reply = ask(prompt(message, examples, with_rules), model=model, provider_name=provider)
        right += predicted_label(reply.text) == truth
        tokens += reply.prompt_tokens
    return right, tokens // len(TEST)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(f"Embeddings: {embedding_provider()}   examples per prompt: {K}   test messages: {len(TEST)}\n")

    teacher = teacher_labels(args.refresh)
    truth = dict(UNLABELED)
    agree = sum(teacher["labels"][m] == truth[m] for m in truth)
    print(f"TEACHER {teacher['model']}: {agree}/{len(truth)} of its labels are right  "
          f"({teacher['input_tokens']} input + {teacher['output_tokens']} output tokens, {teacher['seconds']} s, one time only)")
    for m in truth:
        if teacher["labels"][m] != truth[m]:
            print(f"   teacher said {teacher['labels'][m]}, truth {truth[m]}: {m[:70]!r}")
    print()

    pools = {
        "labelled by the teacher": [(m, teacher["labels"][m]) for m in truth],
        "labelled by a human (truth)": list(truth.items()),
        "agent37's 36 hand-written": POOL,
    }
    vectors = {name: embed_texts([m for m, _ in pool], kind="document") for name, pool in pools.items()}
    rows = [("no help (label names only)", lambda m: ([], False)),
            ("the rules in words (like the teacher)", lambda m: ([], True))]
    rows += [(f"3 similar examples, {name}", (lambda m, n=name: (nearest(m, pools[n], vectors[n]), False))) for name in pools]

    print(f"{'what the student is given':<48}" + "".join(f"{s[0]:>26}" for s in STUDENTS))
    for label, pick in rows:
        cells = []
        for student in STUDENTS:
            right, tokens = score(student, pick)
            cells.append(f"{right:>2}/{len(TEST)}  ({tokens} tok/msg)")
        print(f"{label:<48}" + "".join(f"{c:>26}" for c in cells))
