# agent25_multiturn_evals: cases, easiest first

Concept: evaluating a CONVERSATION, not a single question. Agent13 tested one question at a time. Many failures only show up on the
second or third turn: the agent forgets what "it" refers to, skips a tool it used before, or starts guessing.
Topic: a school lunch menu agent (`agent.py`) with two tools, `get_lunch(day)` and `get_allergens(dish)`.
Files:
- `lunch.evalset.json`: 3 conversations (2-3 turns each). Later turns say "it" or "and what about Friday then?".
- `multiturn_config.json`: how to score each turn: exact tool calls, and an LLM judge on the answer.
- `rubric_config.json`: a different way to score: three written rubrics ("the answer is short", "no invented allergens", ...).
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT25_MODEL_PROVIDER` for this agent only.
You can also chat with it by hand: `uv run adk run agent25_multiturn_evals`.

## How it works
```
 lunch.evalset.json
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ case: follow_up_it                                                         │
 │  turn 1  "What's for lunch on Tuesday?"   expect tool get_lunch(Tuesday)   │
 │  turn 2  "Does it contain nuts?"          expect tool get_allergens("Chicken satay")  ◄── needs turn 1
 │  turn 3  "And what is for lunch on Wednesday?"  expect tool get_lunch(Wednesday)
 └──────────────┬─────────────────────────────────────────────────────────────┘
                │ the eval runner plays the turns, in order, in ONE session
                ▼
        ┌───────────────┐  turn 1 ─► actual tool calls + answer ─► compare ─► PASS / FAIL for turn 1
        │ real agent    │  turn 2 ─► actual tool calls + answer ─► compare ─► PASS / FAIL for turn 2
        └───────────────┘  turn 3 ─► ...
        the case score = average over its turns, so one bad turn gives e.g. 0.67
```

## Case 1: run the conversation evals
    uv run adk eval agent25_multiturn_evals agent25_multiturn_evals/lunch.evalset.json \
        --config_file_path agent25_multiturn_evals/multiturn_config.json --print_detailed_results

Expect (from testing):

| | follow_up_it | weekend_then_friday | gluten_check | passed |
|---|---|---|---|---|
| Gemini | pass | **fail** (trajectory 0.5, answers right) | pass | 2 / 3 |
| local `qwen3.5-9b` | **fail** (0.67) | **fail** (0.0) | pass | 1 / 3 |

Learn: a conversation case gets a score per turn, averaged. So `0.67` means "two turns right, one turn wrong". The report shows
where it went wrong.

## Case 2: a right answer with the wrong path (Gemini, `weekend_then_friday`)
Open the details for `weekend_then_friday`.
Expect: `final_response_match_v2` passes with 1.0, but `tool_trajectory_avg_score` is 0.5. For "What's for lunch on Saturday?" Gemini
answered "There is no lunch on Saturday" without calling `get_lunch`. The eval set expects a tool call on every turn.
Learn: the answer is right, so is it a failure? The agent skipped the tool because it already knew school lunch is Monday to Friday.
That might be fine, or you might require a tool call so that the menu stays the single source of truth. The eval does not decide that
for you. You either change the expectation or the agent.

## Case 3: a turn that collapses (local model)
In the details for the local run, find `weekend_then_friday` and `follow_up_it`.
Expect: in the later turns, the model made NO tool call and invented an answer, for example "The lunch for Friday is not available in the
current menu data" and "The lunch on Wednesday is not available". Both are wrong: the menu has both days.
Learn: this is the failure that single-question tests cannot see. Turn 1 is always fine. After a turn without a tool, a small model tends
to repeat that pattern ("not available") instead of calling the tool again. We saw the same thing in agent10 and agent20.

## Case 4: score the answer by written rules (rubrics)
    uv run adk eval agent25_multiturn_evals agent25_multiturn_evals/lunch.evalset.json \
        --config_file_path agent25_multiturn_evals/rubric_config.json --print_detailed_results

Expect (Gemini): 3 of 3 cases pass, but the rubric `uses_earlier_turn` scores below 1.0 on two cases (0.67 and 0.5) although the agent really did
use the earlier turn.
Learn: a rubric is a plain-English check ("The response does not mention any allergen unless the tools returned it"). It is useful when there is
no single right answer to compare against. Use it for qualities such as tone, length or honesty.

## Case 5: the judge sees one turn at a time
Look at the per-turn reasoning for `gluten_check` in the rubric run (it is stored in `.adk/eval_history/`).
Expect: for turn 2 ("My daughter can't eat gluten. Is it okay for her?") the judge scored `uses_earlier_turn` 0.0 with the reasoning
"Since this is the first turn, no dish was 'just discussed'". It evaluated that turn without the conversation before it.
Learn: this rubric metric scores each turn in isolation, so it cannot check anything that depends on earlier turns. A rubric about
"remembers the previous turn" gives false failures. For properties of the whole conversation ADK has multi-turn metrics, see case 6.

## Case 6: whole-conversation metrics (tried, does not work here)
ADK lists `multi_turn_task_success_v1`, `multi_turn_trajectory_quality_v1` and others. In this repo, with these package versions, running
`multi_turn_task_success_v1` failed inside Google's evaluation library with `TypeError: Unsupported dataset type ... EvaluationDataset`, and
the metric came back as NOT_EVALUATED. (The same library cannot be upgraded here: see the note about `google-cloud-aiplatform` in agent13.)
Learn: experimental features can break between versions. The turn-by-turn metrics in cases 1-5 do work, so build on those, and check a
new metric on a tiny case before depending on it.

## Case 7: break the context on purpose and watch the eval notice
`agent.py` has a deliberate bug you can switch on: `FORGET_HISTORY=1` adds a `before_model_callback` that removes everything before the
latest user message, so the model never sees the earlier turns.

    FORGET_HISTORY=1 MODEL_PROVIDER=gemini uv run adk eval agent25_multiturn_evals agent25_multiturn_evals/lunch.evalset.json \
        --config_file_path agent25_multiturn_evals/multiturn_config.json --print_detailed_results

Expect (Gemini, from testing; the buggy runs were repeated 3 times with the same outcome):
- `follow_up_it`: turn 2 ("Does it contain nuts?") becomes "I need to know which dish you are asking about. Which dish are you referring to?" Trajectory score 0.67.
- `gluten_check`: turn 2 becomes "What dish are you asking about?" Trajectory score 0.5.
- `tool_trajectory_avg_score` FAILS on both cases. `final_response_match_v2` still shows 1.0 on them, even though the answer to turn 2 is a
  question and not "Vegetable soup contains celery but no gluten".
Learn: two lessons. First, the multi-turn eval notices lost context: the failing turn is exactly the one that needs the earlier turn.
Second, the LLM judge missed it every time here, while the plain tool-call check caught it. Do not rely on one metric. Keep a strict,
mechanical check next to the judge. (Why the judge passed a non-answer is not known; treat it as a weakness of this metric.)

Also note: simply telling the model "treat every message as a new question, do not use earlier messages" did NOT break it. Gemini passed 3 of
3 cases anyway, because ADK still sends the history and the model uses it. A lost-context bug is a code or configuration bug, not a prompt.
Restore normal behaviour by running without `FORGET_HISTORY`.

## Case 8: what is not covered here
- User simulation: ADK can also make a model play the user from a short plan ("ask about Tuesday, then ask if it is nut-free"), so you do
  not write every turn. That needs the same Google evaluation library as case 6 and was not run.
- Three conversations are a tiny sample. A real set grows with every bug you find (see agent13, case 9).
