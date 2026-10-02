"""Lab 39: what does an answer COST, in tokens and in seconds? Four ways to spend less.

Run:   uv run python agent39_cost_speed/cost_lab.py                  (Gemini: three model sizes, about 10 minutes; Pro thinks a lot)
       uv run python agent39_cost_speed/cost_lab.py --with-local     (adds the local model as a fourth row)
       uv run python agent39_cost_speed/cost_lab.py --part 3         (one part only; parts 1, 2, 3, 4)

Parts 2-4 always use Gemini (model sizes and caching are Gemini features); only part 1 can add the local model.
Bills for language models are counted in TOKENS (pieces of words): input tokens (everything you send) and output tokens (everything the
model writes; for Gemini this includes its hidden "thinking" tokens). Bigger models cost more per token and are slower. No prices are
printed here because they change; look up the current price list and multiply.
  PART 1  model size:     same 12 questions on small / medium / large models: accuracy, tokens, seconds
  PART 2  a router:       a cheap call decides EASY or HARD, and only hard questions go to the large model
  PART 3  an output cap:  limit the length of the answer, and see what that does to the answer
  PART 4  caching:        send the same long text again and again: Gemini may charge less for the repeated part
"""
import argparse
import re
import time
from dataclasses import dataclass

from common.llm import Reply, ask
from common.rag import load_handbook

SMALL, MEDIUM, LARGE = "gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"

# (question, text the right answer contains). Easy ones need one fact; hard ones need several steps.
EASY = [
    ("What is the capital of Australia?", "canberra"),
    ("What is 15 times 4?", "60"),
    ("How many days are there in a leap year?", "366"),
    ("Who wrote the play Romeo and Juliet?", "shakespeare"),
    ("What is the chemical symbol for gold?", "au"),
    ("What is 144 divided by 12?", "12"),
]
HARD = [
    ("Anna is twice as old as Ben. In 6 years the sum of their ages will be 42. How old is Anna now?", "20"),
    ("Pens cost 3 for 4 dollars, sold only in groups of 3. I have 50 dollars but must keep 2 dollars for a bag. How many pens can I buy?", "36"),
    ("How many two-digit numbers are divisible by 7?", "13"),
    ("What is the sum of all whole numbers from 1 to 100 that are NOT divisible by 3?", "3367"),
    ("A bag has 3 red, 4 blue and 5 green marbles. I take 2 without putting any back. What is the probability that both are the same colour? Give a fraction.", "19/66"),
    ("An empty tank holds 120 litres. A tap adds 8 litres per minute while a leak removes 3 litres per minute. How many minutes until it is full?", "24"),
]
QUESTIONS = EASY + HARD
SYSTEM = "Answer the question. Show at most two short lines of working, then end with 'Answer: <answer>'."


@dataclass
class Totals:
    right: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


def is_right(reply: str, expected: str) -> bool:
    text = reply.lower().replace(",", "")
    final = text.rsplit("answer:", 1)[-1] if "answer:" in text else text
    return re.search(rf"(?<![\d/.]){re.escape(expected)}(?![\d/])", final) is not None


def run_questions(questions, model: str, provider: str = "gemini") -> Totals:
    totals = Totals()
    for question, expected in questions:
        reply = ask(question, system=SYSTEM, model=model, provider_name=provider)
        totals.right += is_right(reply.text, expected)
        totals.input_tokens += reply.prompt_tokens
        totals.output_tokens += reply.output_tokens
        totals.seconds += reply.seconds
    return totals


def part1(with_local: bool) -> None:
    print("PART 1: the same 12 questions (6 easy, 6 hard: several steps) on different model sizes\n")
    print(f"  {'model':<24} {'easy right':>10} {'hard right':>10} {'input tok':>10} {'output tok':>11} {'seconds':>8}")
    rows = [(SMALL, "gemini"), (MEDIUM, "gemini"), (LARGE, "gemini")] + ([("local model", "local")] if with_local else [])
    for model, provider in rows:
        easy = run_questions(EASY, None if provider == "local" else model, provider)
        hard = run_questions(HARD, None if provider == "local" else model, provider)
        print(f"  {model:<24} {easy.right:>7}/{len(EASY)} {hard.right:>7}/{len(HARD)} {easy.input_tokens + hard.input_tokens:>10} "
              f"{easy.output_tokens + hard.output_tokens:>11} {easy.seconds + hard.seconds:>8.0f}")
    print("\n  Read the tokens and the seconds as well as the accuracy: the larger models also THINK more, so they write more output tokens.\n")


def part2() -> None:
    print("PART 2: a router. The small model first labels each question EASY or HARD (about 1 output token); only HARD goes to the large model.\n")
    easy_or_hard = "Is this question EASY (one fact or one simple calculation) or HARD (needs several steps of reasoning)? Reply with only EASY or HARD.\n\nQuestion: "
    print(f"  {'strategy':<30} {'right':>7} {'input tok':>10} {'output tok':>11} {'seconds':>8}   large-model calls")
    for name, plan in [("everything to the small model", "small"), ("everything to the large model", "large"), ("routed", "routed")]:
        totals, large_calls = Totals(), 0
        for question, expected in QUESTIONS:
            model = SMALL if plan == "small" else LARGE
            if plan == "routed":
                label = ask(easy_or_hard + question, model=SMALL, max_tokens=5, provider_name="gemini")
                totals.input_tokens += label.prompt_tokens
                totals.output_tokens += label.output_tokens
                totals.seconds += label.seconds
                model = LARGE if "HARD" in label.text.upper() else SMALL
            reply = ask(question, system=SYSTEM, model=model, provider_name="gemini")
            large_calls += model == LARGE
            totals.right += is_right(reply.text, expected)
            totals.input_tokens += reply.prompt_tokens
            totals.output_tokens += reply.output_tokens
            totals.seconds += reply.seconds
        print(f"  {name:<30} {totals.right:>4}/{len(QUESTIONS)} {totals.input_tokens:>10} {totals.output_tokens:>11} {totals.seconds:>8.0f}   {large_calls}")
    print("\n  A router adds one cheap call per question. It pays off when most questions are easy and the router is right about which is which.\n")


def part3() -> None:
    print("PART 3: capping the length of the answer (max output tokens), on the medium model\n")
    question = "Explain why the sky is blue."  # an open question, so the answer can be long
    for cap in (None, 60, 20):
        reply: Reply = ask(question, model=MEDIUM, max_tokens=cap, provider_name="gemini")
        print(f"  cap={cap!s:<5} output tokens {reply.output_tokens:>4}, {reply.seconds:.1f} s -> {reply.text[:110]!r}")
    asked = ask(question + " Answer in at most 20 words.", model=MEDIUM, provider_name="gemini")
    print(f"  asked for 20 words:  output tokens {asked.output_tokens:>4}, {asked.seconds:.1f} s -> {asked.text[:110]!r}\n")
    print("  A cap is a hard stop, and on Gemini 2.5 the hidden thinking tokens count against it: a small cap can be used up by thinking, so the visible answer is EMPTY")
    print("  (the output tokens above are all thinking). Asking for a short answer keeps the sentence whole, but the thinking still costs tokens.\n")


def part4() -> None:
    print("PART 4: sending the same long text again and again (context caching), on the medium model\n")
    handbook = load_handbook()
    long_text = "\n\n".join(f"=== Copy {i + 1} of the handbook ===\n{handbook}" for i in range(6))
    questions = ["Who is the director?", "How much is the late fee for a book?", "What does colour printing cost?"]
    print(f"  the repeated text is about {len(long_text.split()) * 4 // 3} tokens\n")

    print("  a) automatic: just send the long text first and the question last, every time")
    for question in questions:
        reply = ask(f"{long_text}\n\nUsing the handbook above, answer in one short sentence. Question: {question}", model=MEDIUM, provider_name="gemini")
        print(f"     input tokens {reply.prompt_tokens:>5}, served from cache {reply.cached_tokens:>5}, {reply.seconds:>5.1f} s -> {reply.text[:45]!r}")

    print("\n  b) explicit: store the long text in a cache once, then refer to it")
    from google import genai
    from google.genai import types
    client = genai.Client()
    cache = client.caches.create(model=MEDIUM, config=types.CreateCachedContentConfig(
        contents=[types.Content(role="user", parts=[types.Part(text=long_text)])],
        system_instruction="Answer questions about the handbook in one short sentence.", ttl="300s"))
    try:
        for question in questions:
            start = time.time()
            result = client.models.generate_content(model=MEDIUM, contents=question, config=types.GenerateContentConfig(cached_content=cache.name))
            usage = result.usage_metadata
            print(f"     input tokens {usage.prompt_token_count:>5}, served from cache {usage.cached_content_token_count:>5}, {time.time() - start:>5.1f} s -> {result.text.strip()[:45]!r}")
    finally:
        client.caches.delete(name=cache.name)   # a cache is billed for storage until it expires, so remove it when done
    print("\n  The cached part of the input is billed at a lower rate. Automatic caching is a bonus that may or may not happen; the explicit cache is a promise you pay storage for,")
    print("  and it only makes sense when many questions share one long text. Both need the long, unchanging text FIRST.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--with-local", action="store_true")
    args = parser.parse_args()
    parts = {1: lambda: part1(args.with_local), 2: part2, 3: part3, 4: part4}
    for number in ([args.part] if args.part else [1, 2, 3, 4]):
        parts[number]()
