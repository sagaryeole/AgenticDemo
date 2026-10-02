# agent42_supervisor_critic: cases, easiest first

Concept: a supervisor. One agent manages a team of specialists and decides, while the work is going on, who does what next. It does none of the
work itself. It calls its team members as tools (agent14), reads what comes back, and routes it on: a planner, a writer, and a fact checker who
can send the draft back for repair.
Compare with the fixed pipelines of agents 08-10: `SequentialAgent` always runs the same steps in the same order, and `LoopAgent` repeats a fixed
pair of agents. Here the order and the number of rounds are the supervisor's decision, made by the model, one step at a time.
Topic: short texts about the Moon, Mars or the octopus for students. The checker's source of truth is a tiny fact sheet in `agent.py` (`lookup_fact`).
Run: `uv run adk run agent42_supervisor_critic`
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT42_MODEL_PROVIDER` for this agent only.
The agent prints `[supervisor -> planner]`, `[supervisor -> writer]` ... with the start of what the supervisor passed to each tool.

## How it executes
Control: the supervisor's LLM chooses every step. The specialists never talk to the user and never call each other.

```
 user: "Write a short text about the Moon. Be sure to include that it is about 500,000 km from Earth."
        │
        ▼
 ┌───────────┐ 1. planner(request) ───────────────► 3 numbered points
 │ SUPERVISOR│ 2. writer(plan + what the user asked) ► draft
 │   (LLM)   │ 3. fact_checker(draft) ──► lookup_fact("moon") ──► "PROBLEMS: 500,000 km is wrong, it is 384,400 km"
 │           │ 4. writer(draft + the problems) ───► corrected draft            ◄─┐ repeat, at most 2 rewrites
 │           │ 5. fact_checker(new draft) ────────► "OK"  ────────────────────────┘ (stops as soon as the answer is OK)
 └─────┬─────┘
       ▼ final text + a note about what was corrected + "Checked: OK after 1 rewrite(s)."
```

## Case 1: the checker catches a wrong claim
> Write a short text about the Moon for students. Be sure to include that the Moon is about 500,000 km from Earth.

Expect (from testing, both models): the calls planner, writer, fact_checker, writer, fact_checker. The first draft contains 500,000 km because the user asked for it,
the fact checker looks up the Moon and reports that the distance is 384,400 km, and the second draft says 384,400 km. The last line reads
`Checked: OK after 1 rewrite(s).` Gemini also added "The distance you provided (500,000 km) was corrected to 384,400 km." The local model corrected the text
but did not tell the user about the correction.
Learn: the writer wrote what it was asked to write. It took a separate agent with a separate source of truth to catch the error. Checking your own work with the
same knowledge that produced the mistake does not work as well.

## Case 2: the supervisor decides how many rounds
> Write a short text about the Moon for students: its size, its distance and how long it takes to orbit Earth.

Expect (from testing): the number of rewrites varies between runs. Gemini needed 2 rewrites in one run (the writer had said the Moon is "about one-quarter our
planet's size" and "its rotation period is also about 27.3 days", and the checker would not accept loose claims) and 0 in another. The local model needed 1.
Learn: this is the difference from a `LoopAgent`, which would run a fixed number of rounds. The supervisor repeats while the checker is unhappy and stops when it says OK,
up to the cap of 2 rewrites in its instruction. The cap matters: without it, a strict checker and a stubborn writer could go on forever.

## Case 3: each specialist has one job
Read the three `instruction`s in `agent.py`.
Learn: the planner only plans, the writer only writes (and rewrites when given a list of problems), the checker only checks and "does not rewrite the draft".
Narrow jobs are easy to write, easy to test one by one, and the checker's "reply exactly OK" gives the supervisor something simple to branch on.

## Case 4: what the supervisor must pass on
Look at the `[supervisor -> writer]` lines. The second one starts with the draft, followed by the problems.
Learn: the specialists have no memory of each other. Whatever the supervisor does not put into a call, the specialist does not know. The instruction says "call writer again
with the full draft plus the full list of problems" for exactly this reason: if the supervisor sends only "fix it", the writer cannot.

## Case 5: try a topic with no facts
> Write a short text about volcanoes. Include that the biggest one is 50 km tall.

Expect: not tested here. The fact sheet only has the moon, mars and octopus, so `lookup_fact` answers "No facts stored for this topic". Think about what you want
the checker to do then (it should not say OK), and edit the checker's instruction to say so.
Learn: a checker is only as good as its source of truth. Without a fact source, the checker would use its own memory: another opinion, not a check.

## Case 6: cost
Count the model calls in case 1: supervisor (several turns), planner, writer, checker (twice, each with a lookup), writer again, plus the supervisor's own turns.
Learn: a team multiplies calls. It costs more and takes longer than one agent writing one text (agent39 shows how to measure that). Use a team when the check or the
division of work is worth it, as with facts that must be right, and not for a task a single call handles well.

## Case 7: supervisor, transfer, pipeline or loop?
| | Who decides the order | Good for |
|---|---|---|
| `SequentialAgent` (agent08) | you, fixed | steps that are always the same |
| `LoopAgent` (agent10) | you: repeat a fixed group of steps | "improve until good enough", same steps each round |
| transfer (agent07) | the model: hands the conversation over | routing a user to the right specialist |
| supervisor with `AgentTool` (agent14, here) | the model, step by step, and it keeps control | work where the next step depends on the last result |

Learn: the more the model decides, the more flexible, and the less predictable. Start with a fixed pipeline, and move to a supervisor when the steps really must change.
