"""Run one agent over many items: in parallel, with retries, and safe to stop and restart.

Run:   uv run python agent47_batch_processing/batch.py --concurrency 1,4,8       compare speeds (a table)
       uv run python agent47_batch_processing/batch.py --concurrency 4 --fail-rate 0.3     simulate flaky calls: retries rescue them
       uv run python agent47_batch_processing/batch.py --concurrency 4 --limit 15          stop after 15 items ...
       uv run python agent47_batch_processing/batch.py --concurrency 4 --resume            ... and carry on: only the missing 21 run
Add MODEL_PROVIDER=local in front for the local model.

What a batch job needs that a chat does not:
  CONCURRENCY  several items at once (a semaphore limits how many), because most of the time is spent waiting for the model
  RETRIES      a call can fail (429, a network blip); wait a little longer each time and try again, a few times
  RESULTS      one line per item written to a file AS SOON AS it is done, so a crash loses almost nothing
  RESUME       items that already have a result are skipped, so the job can be restarted
Results go to agent47_batch_processing/results.csv (ignored by git).
"""
import argparse
import asyncio
import csv
import random
import time
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent47_batch_processing.agent import root_agent
from agent47_batch_processing.reviews import REVIEWS

RESULTS = Path(__file__).resolve().parent / "results.csv"
MAX_ATTEMPTS = 4


async def label_one(runner: InMemoryRunner, text: str) -> str:
    """One model call for one review, in a fresh session so the items cannot influence each other."""
    session = await runner.session_service.create_session(app_name="batch", user_id="batch")
    async for event in runner.run_async(user_id="batch", session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=text)])):
        pass
    session = await runner.session_service.get_session(app_name="batch", user_id="batch", session_id=session.id)
    return session.state["result"]["label"]


async def process_item(index: int, text: str, runner, gate: asyncio.Semaphore, fail_rate: float, stats: dict, writer, file) -> None:
    async with gate:   # at most `concurrency` items run at the same moment
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if random.Random(f"{index}-{attempt}").random() < fail_rate:   # a pretend failure, the same every run
                    raise ConnectionError("simulated network error")
                label = await label_one(runner, text)
                writer.writerow([index, label, attempt])
                file.flush()   # written now, not at the end
                stats["done"] += 1
                stats["retries"] += attempt - 1
                return
            except Exception as error:
                if attempt == MAX_ATTEMPTS:
                    stats["failed"].append((index, type(error).__name__))
                    return
                await asyncio.sleep(0.5 * 2 ** (attempt - 1))   # wait 0.5 s, 1 s, 2 s ... before the next try


async def run(concurrency: int, fail_rate: float, limit: int | None, resume: bool) -> dict:
    done_before = set()
    if resume and RESULTS.exists():
        done_before = {int(row[0]) for row in csv.reader(RESULTS.open()) if row and row[0].isdigit()}
    items = [(i, text) for i, (text, _) in enumerate(REVIEWS) if i not in done_before]
    if limit:
        items = items[:limit]
    stats = {"done": 0, "retries": 0, "failed": []}
    runner = InMemoryRunner(agent=root_agent, app_name="batch")
    gate = asyncio.Semaphore(concurrency)
    start = time.time()
    with RESULTS.open("a" if resume else "w", newline="") as file:
        writer = csv.writer(file)
        if not resume:
            writer.writerow(["index", "label", "attempts"])
        await asyncio.gather(*(process_item(i, t, runner, gate, fail_rate, stats, writer, file) for i, t in items))
    stats.update(seconds=time.time() - start, attempted=len(items), skipped=len(done_before))
    return stats


def accuracy() -> tuple[int, int]:
    rows = [row for row in csv.reader(RESULTS.open()) if row and row[0].isdigit()]
    right = sum(row[1] == REVIEWS[int(row[0])][1] for row in rows)
    return right, len(rows)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", default="4", help="a number, or several separated by commas to compare, e.g. 1,4,8")
    parser.add_argument("--fail-rate", type=float, default=0.0, help="chance that an attempt fails on purpose (0 to 1)")
    parser.add_argument("--limit", type=int, default=None, help="process only this many items")
    parser.add_argument("--resume", action="store_true", help="keep results.csv and skip items that already have a result")
    args = parser.parse_args()
    print(f"{len(REVIEWS)} reviews, retries: up to {MAX_ATTEMPTS} attempts each, simulated failure rate {args.fail_rate}\n")
    print(f"{'concurrency':>11} {'items run':>9} {'skipped':>8} {'done':>5} {'failed':>7} {'retries used':>13} {'seconds':>8} {'right':>9}")
    for concurrency in (int(c) for c in args.concurrency.split(",")):
        s = await run(concurrency, args.fail_rate, args.limit, args.resume)
        right, total = accuracy()
        print(f"{concurrency:>11} {s['attempted']:>9} {s['skipped']:>8} {s['done']:>5} {len(s['failed']):>7} {s['retries']:>13} {s['seconds']:>8.1f} {right:>5}/{total}")
        for index, name in s["failed"]:
            print(f"            gave up on item {index}: {name}")


asyncio.run(main())
