# agent10_loop: cases, easiest first

Run: `uv run adk run agent10_loop`, or `uv run adk web` to see each round and the state.
Concept: `LoopAgent` repeats its sub-agents until a stop condition is met.
Topic: a slogan writer and a critic. The critic checks three rules and either approves or sends feedback.
Rules: at most 6 words, names the product, no exclamation mark.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT10_MODEL_PROVIDER` for this agent only.

## How it executes
Control: FIXED STRUCTURE with a REPEAT. The order inside a round is set in code. How many
rounds run depends on the critic, but never more than `max_iterations`.

```
 user: "a reusable water bottle"
        │
        ▼    slogan_loop (LoopAgent, max_iterations = 4)
 ╔═══════════════════════════════════════════════════════════════╗
 ║                                                               ║
 ║   ┌────────┐ state["draft"]  ┌────────┐                       ║
 ║   │ writer ├────────────────►│ critic │                       ║
 ║   └───▲────┘                 └───┬────┘                       ║
 ║       │                          │                            ║
 ║       │   rules NOT met          │   rules met                ║
 ║       │   state["feedback"]      │   check_slogan() approves  ║
 ║       └──────────────────────────┤   (escalate = True)        ║
 ║                                  │                            ║
 ╚══════════════════════════════════╪════════════════════════════╝
        ▲ repeat                    ▼
        │                       loop ends
        └── also ends after round 4, approved or not (safety net)
```

## Case 1: the loop runs and improves the draft
> a reusable water bottle

Expect: alternating `[writer]` and `[critic]` lines. The critic names the rule that failed,
and the next draft changes to fix it.
Learn: a loop is a draft, check and revise cycle. Each round uses the last round's output.

## Case 2: the code stops the loop
Watch the end of the run.
Expect: the critic replies "Approved" and the run ends right after, with no extra round.
Learn: `check_slogan` sets `tool_context.actions.escalate = True` when every rule passes.
That is how a tool tells a LoopAgent to stop. The word count and the exclamation check run
in Python. Only "does it name the product" is the model's judgement, passed in as `names_the_product`.

## Case 3: the safety net
Watch a run where the critic never approves, or set `max_iterations=2` in `agent.py`.
Expect: the loop stops after the last allowed round even though the draft was rejected.
An easy way to see it: set the rule to `MAX_WORDS = 1` in `agent.py`, so nothing can pass.
Learn: always set `max_iterations`. Without it a loop with a picky critic could run forever,
and every round costs model calls. Change it back afterwards.

## Case 4: feedback travels through state
Run `uv run adk web`, send an idea, open the State after each round.
Expect: `draft` holds the writer's latest slogan and `feedback` holds the critic's last note.
Learn: the writer's `{feedback?}` placeholder is replaced from state. The `?` means
"use it if it exists", which is why round 1 works before any feedback exists.

## Case 5: the model decides how strict the critic is
    AGENT10_MODEL_PROVIDER=local  uv run adk run agent10_loop
    AGENT10_MODEL_PROVIDER=gemini uv run adk run agent10_loop

Expect: the two runs differ. In testing, local kept rejecting ("does not name the product"
even for a draft with "Reusable Bottle" in it) and repeated an earlier draft. Gemini
converged after a few rounds.
Learn: a loop is only as good as its critic, and the critic is a model too. The first version
of this agent let the model count words. The local model said "5 words exceeds the limit of 6",
which is wrong. Moving the count into `check_slogan` fixed it. Use code for rules code can check,
and the model only for judgement. Rule 2 is still judgement, so it can be lenient: Gemini approved
"Understand Your Worth." for a net worth calculator because it contains "Worth".

## Case 6: change the rules
Edit the critic's rules, for example "at most 3 words", and run again.
Expect: more rounds, and a higher chance of hitting `max_iterations`.
Learn: the stop condition is part of the design. Stricter rules mean more loops and more cost.

## Case 7: compare the three workflow agents
| Agent | Runs | Stops when |
|---|---|---|
| agent08 `SequentialAgent` | steps one after another, once | the last step finishes |
| agent09 `ParallelAgent` | steps at the same time, once | all steps finish |
| agent10 `LoopAgent` | steps repeatedly | a step sets `escalate` (here via `check_slogan`), or `max_iterations` |

Learn: choose by the shape of the work. A fixed chain, independent tasks, or "repeat until good".
