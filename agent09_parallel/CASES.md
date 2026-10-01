# agent09_parallel: cases, easiest first

Run: `uv run adk run agent09_parallel`, or `uv run adk web` to see the branches and state.
Concept: `ParallelAgent` runs independent sub-agents at the same time, and a later step merges the results.
Topic: an idea reviewer. Three reviewers (benefits, risks, cost) work at once, then a verdict writer combines them.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT09_MODEL_PROVIDER` for this agent only.

## How it executes
Control: FIXED STRUCTURE, set in code. The three reviewers run AT THE SAME TIME, then the
verdict runs once all three are finished.

```
 user idea
     │
     ▼   idea_review (SequentialAgent)
 ╔═══════════════════════════════════════════════╗
 ║ step 1: review_team (ParallelAgent)           ║
 ║                                               ║
 ║   ┌───────────────────┐ ──► state["benefits"] ║
 ║   │ benefits_reviewer │                       ║
 ║   └───────────────────┘                       ║
 ║   ┌───────────────────┐ ──► state["risks"]    ║   all three start together,
 ║   │ risks_reviewer    │                       ║   the step ends when the
 ║   └───────────────────┘                       ║   slowest one finishes
 ║   ┌───────────────────┐ ──► state["cost"]     ║
 ║   │ cost_reviewer     │                       ║
 ║   └───────────────────┘                       ║
 ╚═════════════════════╤═════════════════════════╝
                       ▼
 step 2: verdict_writer reads {benefits} {risks} {cost}
                       ▼
                 go / wait / no-go
```

## Case 1: one idea, three reviews, one verdict
> Start a vegetable garden at our school

Expect: replies from `benefits_reviewer`, `risks_reviewer`, `cost_reviewer`, then `verdict_writer`.
Learn: one message fans out to three agents, and the results are merged in a final step.

## Case 2: the reviewers do not depend on each other
Look at the three reviews.
Expect: none refers to another's answer. Each only saw your idea.
Learn: use a parallel agent when the sub-tasks are independent. If one needs another's
output, use a `SequentialAgent` (agent08).

## Case 3: each branch has its own state key
Run `uv run adk web`, send an idea, open the session State.
Expect: `benefits`, `risks`, `cost` and `verdict` are all stored.
Learn: parallel branches must write to different `output_key` values. If two shared
one, the later write would overwrite the earlier one.

## Case 4: fan out, then fan in
Open `agent.py` and read the last lines.
Expect: `root_agent` is a `SequentialAgent` of `[review_team, verdict_writer]`.
Learn: workflow agents nest. The parallel step finishes completely before the verdict
step starts, which is why `{benefits}`, `{risks}` and `{cost}` all exist by then.

## Case 5: does it actually run in parallel? (experiment)
Time one run, then change `review_team` from `ParallelAgent` to `SequentialAgent`, and time it again.
Expect: with a hosted model like Gemini the sequential version is slower. With a local
model the difference may be small, because LM Studio may process one request at a time.
Learn: parallel only saves time if the model backend can actually serve calls at once.
Change it back afterwards.

## Case 6: the same idea, different models
    AGENT09_MODEL_PROVIDER=local  uv run adk run agent09_parallel
    AGENT09_MODEL_PROVIDER=gemini uv run adk run agent09_parallel

Expect: similar bullets, but possibly different verdicts. In testing, the local model said
"Go" and Gemini said "Wait" for the same school-garden idea.
Learn: the verdict is the model's judgement, not a fact. Different models weigh the same
inputs differently, so important decisions need a human or an evaluation.

## Case 7: a vague idea
> something cool

Expect: depends on the model. Gemini's reviewers were thin ("lack of definition"), the cost
reviewer said it could not estimate, and the verdict was "Wait". A weaker model may
invent details instead.
Learn: nothing in the workflow checks the input. Whether bad input is caught depends on
the model and the instructions, so add an explicit check if it matters.
