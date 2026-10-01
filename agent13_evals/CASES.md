# agent13_evals: cases, easiest first

Concept: evals. Instead of typing questions by hand and eyeballing the answers, you write the questions
and the expected behaviour down once, and ADK runs them against the agent and scores the result.
Topic: a bookshop assistant (`agent.py`) tested by 6 eval cases (`bookshop.evalset.json`).

Files:
- `agent.py`: the agent being tested (function tools over a 5-book catalogue).
- `bookshop.evalset.json`: the test cases. Each has a question, the expected tool call, and a reference answer.
- `test_config.json`: how to score. Tool calls must match exactly, and an LLM judge compares the answer to the reference.
- `weak_config.json`: the same, but with a word-overlap score instead of the judge. Used in case 5 to show a blind spot.

## Run it
From the project root:

    uv run adk eval agent13_evals agent13_evals/bookshop.evalset.json \
        --config_file_path agent13_evals/test_config.json

- `adk eval` (unlike `adk run`) does not put the project folder on the import path. The shared `common`
  package is installed into the venv by `uv sync` (see `pyproject.toml`), so the agent's
  `from common.models import ...` still works.
- Add `--print_detailed_results` for scores per case. Prefix with `MODEL_PROVIDER=local` or `gemini` to pick the model.
- Run one case: `agent13_evals/bookshop.evalset.json:book_details`.
- The judge metric calls Gemini even when the agent runs on the local model, so the Google settings must be set.
- Results are saved under `agent13_evals/.adk/eval_history/`.

## How it executes
Control: the eval runner drives the agent, you do not. For each case it plays the question to the real
agent, records what the agent did, and compares that to what you wrote down.

```
 bookshop.evalset.json                          test_config.json
 ┌─────────────────────────────────┐            ┌──────────────────────────────┐
 │ case: book_details              │            │ tool_trajectory_avg_score 1.0│
 │  question:  "Tell me about B003"│            │ final_response_match_v2  0.8 │
 │  expected tool: get_book(B003)  │            └───────────────┬──────────────┘
 │  expected answer: "...Dune..."  │                            │ thresholds
 └───────────────┬─────────────────┘                            │
                 │ question                                     │
                 ▼                                              │
         ┌───────────────┐   runs the real agent (a real model call)
         │ agent13_evals │──► actual tool calls  + actual answer
         └───────────────┘             │                  │
                                       ▼                  ▼
                        ┌──────────────────────┐  ┌────────────────────────┐
                        │ trajectory check     │  │ answer check           │
                        │ same tool, same args?│  │ judge model: does it   │
                        │ (exact, in code)     │  │ mean the same thing?   │
                        └──────────┬───────────┘  └───────────┬────────────┘
                                   └────────► score vs threshold ◄───┘
                                                    │
                                              PASSED / FAILED per case
```

## Case 1: run the evals
Run the command above, on both models.

Expect: `Tests passed: 6`, `Tests failed: 0` on both Gemini and the local `qwen3.5-9b`.
Learn: one command replaces typing six questions by hand, and gives a pass/fail you can repeat.

## Case 2: read what is being checked
Open `bookshop.evalset.json` and look at `author_search`.
Expect: the question, the tool it must call (`find_books_by_author` with `{"author": "Tolkien"}`),
and a reference answer.
Learn: there are two separate things to test. Did the agent take the right action (tool trajectory)?
Did it say the right thing (final response)?

## Case 3: the trajectory check catches a wrong tool
In `bookshop.evalset.json`, change the expected tool for `unavailable_book` from `get_book` with
`{"book_id": "B005"}` to `list_books` with `{}`. Run again.
Expect: 5 passed, 1 failed (`unavailable_book`), with `tool_trajectory_avg_score` at 0.0.
Learn: the check compares tool names and arguments exactly. Revert the edit afterwards.

## Case 4: a case where the agent must NOT call a tool
Look at `no_tool_needed` ("What is a library?").
Expect: its expected tool list is empty, so it fails if the agent calls any tool.
Learn: tests should cover when the agent should stay quiet too, not only when it should act.

## Case 5: the word-overlap metric has a blind spot
Change the reference answer of `unavailable_book` to claim the opposite:
`"Yes, book B005, Foundation by Isaac Asimov, is available."` (B005 is NOT available). Then run twice:

    ... --config_file_path agent13_evals/weak_config.json    # word overlap (ROUGE)
    ... --config_file_path agent13_evals/test_config.json    # LLM judge

Expect: with the weak config the case still PASSES (about 0.89, because nearly every word matches).
With the judge config it FAILS (score 0.0).
Learn: a metric that counts shared words cannot tell "is available" from "is not available". Choose the metric
for what you care about. Judge metrics understand meaning but cost a model call. Revert the edit afterwards.

## Case 6: would an eval have caught the agent12 bug?
Agent12 once had `list_books` without the `available` field, and the model guessed "Available" for every book.
Here the case `list_with_availability` guards against that. Reproduce the bug: in `agent.py` remove
`"available": b["available"]` from `list_books`, then run just that case:

    ... bookshop.evalset.json:list_with_availability --config_file_path agent13_evals/test_config.json

Expect (from testing):
- Gemini: tool trajectory PASSED, but the judge FAILED (score 0.0). It guessed the availability.
- Local model: the judge PASSED but the trajectory FAILED. It noticed the missing information and called
  `get_book` for each book instead, got the right answer by a different route.
- With the weak word-overlap config, Gemini's run failed too, but only at 0.34 against a 0.4 threshold,
  close enough that a small change would have flipped it.
Learn: the eval caught the bug on both models, in different ways. A failing eval tells you something changed;
you still read the details to see if the answer or just the route is different. Restore the field afterwards.

## Case 7: same tests, different model
Run case 1 with `MODEL_PROVIDER=gemini` and again with `MODEL_PROVIDER=local`.
Expect: both pass here. A weaker model may fail some cases, for example by picking another tool or arguments.
Learn: an eval set is a way to compare models, and to check that switching models did not break anything.

## Case 8: exact arguments are strict
The arguments must match exactly. Edit `author_search` to expect `{"author": "J.R.R. Tolkien"}` and run it a few times.
Expect: it fails, every time in testing (3 of 3 on Gemini). The question says "Tolkien", the model passes
`Tolkien`, and the full name never appears. The test was wrong here, not the agent.
Learn: an eval can fail because your expectation is off. Free-text arguments are also where a model may
vary between runs, for example "Tolkien" one time and "J.R.R. Tolkien" another, so write questions that make
the expected argument obvious, or relax the check. Revert afterwards.

## Case 9: what evals do not do
Evals test the cases you wrote. They do not cover questions you did not think of.
Learn: they are a safety net for known behaviour, and each new bug is a good reason to add a case.
That is how `list_with_availability` got here.
