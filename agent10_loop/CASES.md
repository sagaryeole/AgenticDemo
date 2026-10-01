# agent10_loop: cases, easiest first

Run: `uv run adk run agent10_loop`, or `uv run adk web` to see each round and the state.
Concept: `LoopAgent` repeats its sub-agents until a stop condition is met.
Topic: a slogan writer (an LLM) and a checker (plain Python, no model). The checker enforces three rules and
either approves or sends feedback.
Rules: at most 6 words, contains a meaningful word (4+ letters) of the product you named, no exclamation mark.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT10_MODEL_PROVIDER` for this agent only.

## How it executes
Control: FIXED STRUCTURE with a REPEAT. The order inside a round is set in code. How many
rounds run depends on the checker, but never more than `max_iterations`.

```
 user: "a bicycle repair shop"
        │
        ▼    slogan_loop (LoopAgent, max_iterations = 4)
 ╔═══════════════════════════════════════════════════════════════╗
 ║                                                               ║
 ║   ┌────────┐ state["draft"]  ┌─────────┐                      ║
 ║   │ writer ├────────────────►│ checker │  plain Python,       ║
 ║   │ (LLM)  │                 └────┬────┘  no model            ║
 ║   └───▲────┘                      │                          ║
 ║       │   rules NOT met           │   rules met              ║
 ║       │   state["feedback"]       │   escalate = True        ║
 ║       └───────────────────────────┤                          ║
 ║                                   │                          ║
 ╚═══════════════════════════════════╪══════════════════════════╝
        ▲ repeat                     ▼
        │                        loop ends
        └── also ends after round 4, approved or not (safety net)
```

## Case 1: the loop runs and improves the draft
> a bicycle repair shop

Expect: alternating `[writer]` and `[checker]` lines. The checker names the rule that failed
(for example "does not contain any of these words: bicycle, repair, shop"), and the next draft changes to fix it.
Learn: a loop is a draft, check and revise cycle. Each round uses the last round's output.

## Case 2: the code stops the loop
Watch the end of the run.
Expect: the checker replies "Approved" and the run ends right after, with no extra round.
Learn: the checker yields an event with `escalate=True` when every rule passes. That is how a step tells
a LoopAgent to stop. It is also how the feedback reaches the writer: `state_delta={"feedback": ...}`.

## Case 3: the safety net
Set `MAX_WORDS = 0` in `agent.py`, so no slogan can pass, and run again.
Expect: four rounds of rejections, then the loop stops even though nothing was approved.
Learn: always set `max_iterations`. Without it, a rule that can never be met would loop forever, and every
round costs model calls. Change it back afterwards.

## Case 4: feedback travels through state
Run `uv run adk web`, send an idea, open the State after each round.
Expect: `draft` holds the writer's latest slogan and `feedback` holds the checker's last note.
Learn: the writer's `{feedback?}` placeholder is replaced from state. The `?` means
"use it if it exists", which is why round 1 works before any feedback exists.

## Case 5: a step that is not an LLM
Look at `SloganChecker` in `agent.py`. It extends `BaseAgent` and has no model.
Learn: workflow steps are agents, and an agent does not have to call a model. Use code for rules code can check
(word count, a required word). This agent went through two worse versions first, both with an LLM critic:
the model miscounted words ("5 words exceeds the limit of 6"), then it skipped the tool call in later rounds
and copied its earlier rejection, so the loop never ended on approval. A plain-Python checker has neither problem.
In testing it ended on a correct approval in every run, on both Gemini and the local model.

## Case 6: the same loop, different writers
    AGENT10_MODEL_PROVIDER=local  uv run adk run agent10_loop
    AGENT10_MODEL_PROVIDER=gemini uv run adk run agent10_loop

Expect: both models end on an approved slogan. Gemini usually needs fewer rounds. The local model tends to
need more, and may write slogans that are too long on the first try.
Learn: the checker makes the rules model-independent. Only the writing quality depends on the model.

## Case 7: what the rule does not catch
> a net worth calculator

Expect: a slogan like "Know Your True Worth." is approved, because it contains "worth", even though it does not
say "calculator".
Learn: the rule is "contains a word of the product", which is exactly what the code checks and no more. Rules
checked in code are exact but only as smart as you make them. Try tightening it, for example to require every word.

## Case 8: change the rules
Edit the checker, for example `MAX_WORDS = 3`, and run again.
Expect: more rounds, and a higher chance of hitting `max_iterations`.
Learn: the stop condition is part of the design. Stricter rules mean more loops and more cost.

## Case 9: compare the three workflow agents
| Agent | Runs | Stops when |
|---|---|---|
| agent08 `SequentialAgent` | steps one after another, once | the last step finishes |
| agent09 `ParallelAgent` | steps at the same time, once | all steps finish |
| agent10 `LoopAgent` | steps repeatedly | a step sets `escalate`, or `max_iterations` |

Learn: choose by the shape of the work. A fixed chain, independent tasks, or "repeat until good".
