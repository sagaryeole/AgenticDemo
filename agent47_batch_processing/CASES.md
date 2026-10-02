# agent47_batch_processing: cases, easiest first

Concept: batch processing. So far an agent answered one person in a chat. Often the job is the opposite: the same small task for 50, 500 or 5,000 items, with nobody waiting at a keyboard. Then four things matter that a chat does not need:
CONCURRENCY (several items at once, because most of the time is spent waiting for the model), RETRIES (some calls fail), RESULTS WRITTEN AS YOU GO (so a crash loses almost nothing), and RESUME (a restart skips what is already done).
Topic: labelling 36 made-up product reviews of school supplies as positive, negative or neutral (`reviews.py`, each with the right label, so accuracy can be checked).
Files: `agent.py` is the worker (one small agent with a fixed output shape, agent06: a `Literal` label); `batch.py` runs it over all reviews. It is a script, not a chat, so there is no `adk run`.
Run: `uv run python agent47_batch_processing/batch.py --concurrency 1,4,8` (add `MODEL_PROVIDER=local` for the local model). Results go to `agent47_batch_processing/results.csv` (ignored by git), one line per review, written the moment each is done.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT47_MODEL_PROVIDER` for this agent only.

## How it executes
```
 36 reviews ──► a gate (asyncio.Semaphore): at most N items run at the same moment
                 │
        ┌────────┼────────┬────────┐        N = 4 workers shown
        ▼        ▼        ▼        ▼
     item 1   item 2   item 3   item 4  ...  each item:
        │                                       attempt 1 ──fails?──► wait 0.5 s ──► attempt 2 ──fails?──► wait 1 s ──► attempt 3 ... up to 4 attempts, then "gave up"
        ▼                                       success: ONE model call in a fresh session ──► the label
   results.csv   ◄── a line is written and flushed as soon as an item finishes
        ▲
        └── --resume: items already in results.csv are skipped
```

## Case 1: does concurrency help?
    MODEL_PROVIDER=gemini uv run python agent47_batch_processing/batch.py --concurrency 1,4,8
Expect (from testing, 36 reviews):

| concurrency | Gemini | local `qwen3.5-9b` |
|---|---|---|
| 1 | 36.0 s | 58.9 s |
| 4 | 12.9 s (2.8 times faster) | 46.6 s (1.3 times faster) |
| 8 | 4.7 s (7.7 times faster) | not run |

All 36 labels were right in every run. Learn: a model call is mostly waiting, so many calls at once finish much sooner. Gemini's service handles many requests at the same time, so 8 at once was almost 8 times faster. A local model runs on ONE machine and mostly serves
one request at a time, so concurrency 4 helped little. More concurrency is not always better: the service's rate limit (the 429 errors of earlier agents) is the ceiling, so raise it step by step.

## Case 2: calls that fail, and retries
    MODEL_PROVIDER=gemini uv run python agent47_batch_processing/batch.py --concurrency 8 --fail-rate 0.3
`--fail-rate 0.3` makes about 30 percent of ATTEMPTS fail on purpose (a simulated network error; the same attempts fail every run, so it is repeatable).
Expect (from testing): all 36 items finished, using 16 retries (about 10 seconds with Gemini, about 49 with the local model at concurrency 4). On Gemini 35 of 36 labels were right in this run (all 36 in the run without failures); the one wrong label is the model, not the retry.
Learn: with up to 4 attempts, a 30 percent failure rate almost never loses an item (the chance that one item fails 4 times in a row is about 1 in 120). Waiting longer before each try (0.5 s, 1 s, 2 s: "exponential backoff") gives a struggling service time to recover, and avoids hammering it.

## Case 3: when retries run out
    MODEL_PROVIDER=local uv run python agent47_batch_processing/batch.py --concurrency 4 --fail-rate 0.8
Expect (from testing, local): 21 items done, 15 gave up (each prints `gave up on item N: ConnectionError`), 30 retries used. The 21 finished items were all labelled correctly.
Learn: a batch must say what it could NOT do. The script lists the failed items instead of ignoring them, and `results.csv` holds only real results, so a later `--resume` run can try just the missing ones. A silent gap in the results is the worst failure of a batch job.

## Case 4: stop, then resume
    uv run python agent47_batch_processing/batch.py --concurrency 4 --limit 15        (stops after 15 items; stands in for a crash)
    uv run python agent47_batch_processing/batch.py --concurrency 4 --resume          (carries on)
Expect (from testing, local): the first run processes 15 items (15/15 right). The second reports `skipped 15`, processes the remaining 21, and `results.csv` then holds all 36 (36/36 right).
Learn: because every result is written the moment it exists, nothing is lost if the program stops, and a restart does only the missing work. Without that, a crash at item 4,999 of 5,000 means starting over (and paying again).
`--resume` assumes an item always gives the same answer for the same input; for a task where that is not true, store the input too.

## Case 5: why a fresh session per item
Read `label_one` in `batch.py`: it creates a new session for every review.
Learn: if all reviews went through one session, each answer would sit in the history of the next one, the prompt would grow (agent30), and one review could influence the label of another. A batch worker should be stateless: input in, result out.

## Case 6: what is different from a chat agent
| | chat agent | batch worker |
|---|---|---|
| who waits | a person, who wants the first word soon (agent43) | nobody; total time and cost count |
| a failure | the person asks again | must be retried, or listed |
| output | free text | a fixed shape (`Literal` label), easy to check and to save |
| state | the conversation | none: a fresh session per item |
| tools | often | rarely; fewer moving parts |

Learn: for batch work, use the smallest model and the simplest worker that is accurate enough (agent39), a fixed output shape (agent06), and a script that handles the waiting, the failures and the saving.

## Case 7: honest limits
Learn: 36 reviews with clear labels; every run was right except one Gemini label. The speed numbers are one run each, and depend on the machine and the service on that day. The failures are simulated, not real 429 errors. Agents 07 and later already
retry real rate-limit errors inside the model call (`common/models.py`); this script's loop is the second line of defence for everything else. A real job would also log timings and errors to a file (agent26) and respect the service's quota.
