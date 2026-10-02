# agent24_planning: cases, easiest first

Run: `uv run adk run agent24_planning` to chat. To measure, use the evaluation script (case 1 and below).
Concept: how much a model "thinks" before it answers, and ways to encourage it: the model's own thinking, a prompt-based planner, or a tool
that checks its work. This agent is built for measuring, so the main test is a script that counts correct answers.
Topic: logic puzzles with exactly one correct answer, so a result is simply right or wrong.
Files:
- `agent.py`: the agent, with two switches (below).
- `puzzles.py`: four puzzles. Every answer is proven unique by brute force: `uv run python agent24_planning/puzzles.py`.
- `evaluate.py`: runs the puzzles several times and counts correct answers.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT24_MODEL_PROVIDER` for this agent only.

The two switches (environment variables):

| `PLANNER_MODE` | What it does | Works with |
|---|---|---|
| `default` | no planner: whatever the model does by itself (Gemini thinks silently by default) | any model |
| `no_thinking` | Gemini's own thinking switched OFF, as a baseline | Gemini only |
| `thinking` | Gemini's built-in thinking with a 2,048-token budget, and thought summaries shown | Gemini only |
| `plan_react` | a prompt-based planner: write a PLAN, then REASONING and ACTIONS, re-plan if needed, then a FINAL ANSWER | any model, designed for agents with tools |

`CHECKER=on` adds a `check_seating` tool that tells the agent which clues a proposed arrangement breaks (default off).
Defaults: Gemini uses `thinking`, a local model uses `default`.

## How it executes
```
 puzzle ──► model ──► answer                                  PLANNER_MODE=no_thinking: one quick pass, a guess
 puzzle ──► model ──► [ hidden thinking, 1,000-6,000 tokens ] ──► answer              default / thinking
 puzzle ──► model ──► PLAN ──► REASONING ──► ACTION (tool call) ──► REASONING ──► FINAL ANSWER      plan_react
                                    ▲                    │
                                    └── re-plan ◄── result      (the ACTION step needs a tool to call)

 CHECKER=on:   propose an arrangement ──► check_seating ──► "2 clues broken: ..." ──► fix them ──► check again ──► answer
```

## Case 1: the puzzles are proven
    uv run python agent24_planning/puzzles.py

Expect: `seating solutions: ['Eve, Dan, Cleo, Ana, Ben'] -> unique`, `pets: fish owner(s): {'Ben'}`, `schedule: finish at 14:30`,
`seating7 solutions: ['Dan, Finn, Ana, Eve, Ben, Cleo, Gus'] -> unique`.
Learn: when you grade a model, make sure the right answer is really the only right answer. The first versions of two of these puzzles had two
valid answers; the brute-force check caught it before it spoiled the experiment. The 7-seat puzzle is checked by parsing its own clue sentences.

## Case 2: easy puzzles do not need thinking
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode no_thinking --only seating,schedule,pets --repeats 3

Expect (from testing): 9 of 9 correct even with Gemini's thinking switched off.
Learn: a strong model solves small puzzles in one pass. Extra thinking costs tokens and time and adds nothing here. Test whether a technique
helps before you pay for it.

## Case 3: a hard puzzle, with thinking off
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode no_thinking --only seating7 --repeats 4

The `seating7` puzzle has seven people and 17 clues, and asks for the answer only, with no working shown.
Expect (from testing, two separate batches): 2 of 4 correct, and 0 of 3 correct. The wrong answers came back in about 1 to 2 seconds, which is
a guess. `hidden_thinking` is 0 tokens.
Learn: with no room to reason, the model guesses an arrangement that looks plausible.

## Case 4: the same puzzle with Gemini's thinking
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode default --only seating7 --repeats 4
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode thinking --only seating7 --repeats 4

Expect (from testing): 4 of 4 correct for each. In `default` mode the model used 3,356 to 6,208 hidden thinking tokens per answer and took 17 to 40
seconds. In `thinking` mode, with a 2,048-token budget, it used 1,222 to 1,908 tokens (20 to 33 seconds) and also returned a short visible
summary of its thinking.
Learn: thinking is the lever that mattered. The answer is the same, but it was reached by working through the clues, and you pay for those
tokens. A budget caps the cost. In `adk run`, `thinking` mode shows the summary first (for example "Calculating Task Completion: I'm piecing
together the timeline..."), then the answer.

## Case 5: a prompt-based planner (plan_react)
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode plan_react --only seating7 --repeats 4

Expect (from testing, Gemini): unreliable. Over three batches without tools it was right 3 of 3, then 1 of 4, and in an earlier batch 0 of 2 with empty replies.
The wrong runs said: "I cannot answer this question as the necessary tools to solve logic and scheduling puzzles are not available."
Learn: the planner works by changing the prompt, so the model is told to plan and then ACT, and the actions are tool calls. With no tools, the
model sometimes concludes it cannot answer, or tries to call a tool that does not exist (`google:python_interpreter` showed up in the log). A planner is
not free reasoning. It suits an agent that has tools to plan with.

## Case 6: plan_react with a checking tool
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode plan_react --tool on --only seating7 --repeats 4

Expect (from testing): 1 of 3 and 2 of 4 across two batches. The failures were empty replies: the final answer never came back, although the model
had used 11,000 to 12,000 thinking tokens in some of them.
Learn: even with the tool, this planner on this model was not dependable, and it duplicated the thinking Gemini already does by itself. Adding machinery to
a model that already reasons can make things worse. Measure, do not assume.

## Case 7: a checker does not replace reasoning
    MODEL_PROVIDER=gemini uv run python agent24_planning/evaluate.py --mode no_thinking --tool on --only seating7 --repeats 1

Expect (from testing): the run printed more than 20 `[check_seating] ... -> N clue(s) broken` lines (2 to 6 clues broken each time), took 87 seconds, and ended
with a wrong answer, although the instruction says to answer only when all clues are satisfied.
Learn: guess-and-check in a space of 5,040 arrangements goes nowhere without reasoning to guide the guesses. A verification tool helps a model that is
already close, not one that is guessing. Also note the model ignored "only answer when check_seating says OK": a prompt rule is not a guarantee.

## Case 8: the local model reasons out loud
    MODEL_PROVIDER=local uv run python agent24_planning/evaluate.py --mode default --only seating7 --repeats 3

Expect (from testing): 3 of 3 correct, in 141 to 170 seconds each. The visible reply was a long working-out ("To solve this logic puzzle, let's break down the
constraints...") although the question says "with no explanation or working shown", and the answer line was still correct. `hidden_thinking` shows 0 for
this model, because the local server does not report reasoning tokens that way.
Learn: this model reasons in its own output, so it got the hard puzzle right where Gemini with thinking switched off guessed. The evaluator reads the
last line, so it still works. Slower and wordier, but accurate here.

## Case 9: the planner on the local model
    MODEL_PROVIDER=local uv run python agent24_planning/evaluate.py --mode plan_react --only seating7 --repeats 3
    MODEL_PROVIDER=local uv run python agent24_planning/evaluate.py --mode plan_react --tool on --only seating7 --repeats 3

Expect (from testing): 3 of 3 correct without the tool (160 to 229 seconds, with 7,800 to 11,400 characters of visible plan and reasoning), and
3 of 3 correct with the tool (116 to 251 seconds). Whether the model actually called `check_seating` in those runs was not checked.
Learn: the same planner that was erratic on Gemini worked every time on the local model. A planner interacts with the model it runs on, so a result
for one model does not carry over to another. Overall the local model solved the hard puzzle in all 9 runs, in three different configurations, at the price of
two to four minutes per answer.

## Case 10: the measurements are noisy
Run any of the commands above twice.
Expect: different numbers. The tables here come from several separate batches of 3 to 4 runs.
Learn: models are not deterministic, and 4 runs is a very small sample. Use the numbers to see the pattern (thinking helps on the hard puzzle, the planner
was erratic), not as exact scores. Also, Vertex can answer `429 RESOURCE_EXHAUSTED` when calls arrive quickly; `evaluate.py` waits and retries.

## Case 11: what to take away
| Technique | Hard puzzle result (Gemini) | Cost |
|---|---|---|
| nothing (thinking off) | guesses, 2/4 and 0/3 | fastest |
| default / built-in thinking | 4/4 each | 1,200 to 6,200 thinking tokens |
| prompt-based planner | Gemini: erratic, 1/4 to 3/3 without tools. Local: 3/3 | extra prompt, a lot of extra text |
| checker tool without reasoning | wrong after 20+ calls | many model calls |

Learn: the right tool depends on the task and on the model. Gemini with thinking solved it. The local model solved it by reasoning out loud, with or without the
planner. A planner and a checker help most when the model uses tools to gather information or to verify results it already reasoned about.
