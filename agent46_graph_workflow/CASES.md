# agent46_graph_workflow: cases, easiest first

Concept: a workflow drawn as a GRAPH. Agents 08-10 gave you fixed shapes: a line (`SequentialAgent`), a fan-out (`ParallelAgent`) and a repeat (`LoopAgent`). ADK 2 also has a general `Workflow`: you list the steps (nodes) and the arrows between them (edges),
and a step can choose WHICH arrow to follow by returning a route name. A node can be a plain function (no model: instant, free, always the same) or an agent (one model call).
So you decide the structure in code, and the model is used only where judgement is needed.
Topic: homework feedback. The problem is "A pen costs 3 dollars. How much do 4 pens cost?" (the answer is 12). The student replies, and the feedback depends on the TYPE of reply.
Run: `uv run adk run agent46_graph_workflow` and type a reply, for example `3 x 4 = 11`. `adk run` prints each node's output under the node's name. The measurement `flow_test.py` sends 12 replies and checks each took the right branch.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT46_MODEL_PROVIDER` for this agent only. Note: `Workflow` is new in ADK 2, so its details may change between versions (this was written for 2.10).

## How it executes
```
 student: "3 x 4 = 11"
        │
        ▼
 receive (function)      keeps the reply in state, builds "Problem: ... Student's reply: ..."        retries itself if it fails (case 5)
        │
        ▼
 judge (agent, 1 model call)   output_schema = {kind: correct | arithmetic | concept | off_topic}      the only place that JUDGES
        │
        ▼
 route (function)        reads the verdict and returns  Event(route="arithmetic")       ◄── chooses the arrow, in code
        │
        ├── "correct"    ──► praise (agent)          "Well done: 12 dollars is right."
        ├── "arithmetic" ──► fix_arithmetic (agent)  "Your method is right, but 3 x 4 = 12."
        ├── "concept"    ──► reteach (agent)         "4 pens at 3 dollars each means 4 groups of 3, so multiply."
        └── "off_topic"  ──► redirect (function)     fixed text, NO model call
                    │
                    ▼  (all four branches meet here)
 finish (function)       adds the footer "(Homework feedback bot)" and sends the message
```

## Case 1: one reply, step by step
    uv run adk run agent46_graph_workflow
> 3 x 4 = 11

Expect (from testing, local model):
```
[judge]: {"kind": "arithmetic"}
[route] verdict: arithmetic
[fix_arithmetic]: Your method of multiplying the cost by the quantity is correct, but the final calculation is wrong because 3 times 4 equals 12.
[homework_feedback]: Your method ... equals 12.

(Homework feedback bot)
```
Learn: each node speaks under its own name, so you can see the path: judge, route, one branch, then the end. Only ONE branch ran; the other three never started.

## Case 2: four kinds of reply
Try `12 dollars`, `3 x 4 = 11`, `I add them: 7` and `what is for lunch?`.
Expect (from testing, local): the branches `praise`, `fix_arithmetic`, `reteach` and the fixed redirect, in that order, each with feedback that fits ("4 pens at 3 dollars each means 4 groups of 3, which requires multiplication rather than addition").
Learn: every branch has its own short instruction. A single agent with one long prompt would have to describe all four cases at once and hope the model picks the right one; here the choice is made once, by the judge, and the rest follows the edges.

## Case 3: a branch without a model
Type `what is for lunch?`.
Expect (from testing): the nodes that ran are the workflow and the judge only. The reply is the fixed sentence "That does not look like an answer to the problem. Please try again: A pen costs 3 dollars. How much do 4 pens cost?"
Learn: `redirect` is a plain function. One model call (the judge) instead of two, no chance of a strange reply, and no cost. Whatever can be decided or written in code should be.

## Case 4: how reliable is the routing?
    uv run python agent46_graph_workflow/flow_test.py
(add `MODEL_PROVIDER=local` in front for the local model, `--show` for the feedback texts.)
Expect (from testing, 12 replies: 3 correct, 3 arithmetic, 3 concept, 3 off-topic): Gemini 12/12, local 11/12. The local model's miss: the reply `7 dollars` went to `fix_arithmetic` instead of `reteach`.
Learn: the structure is exact; only the judge's verdict can be wrong, and that one decision is easy to test with a list of examples like this. The `7 dollars` miss is arguable: a bare number gives no sign of the method used. Where the verdict is uncertain, give the judge a rule
for it in its instruction, or add a fifth route ("unclear") that asks the student to show their working.

## Case 5: a step that fails and tries again
    FLAKY=1 uv run adk run agent46_graph_workflow
> 12 dollars

Expect (from testing, local): the `receive` step raises a simulated `ConnectionError` and ADK prints "Node receive failed and is being retried locally"; the run then continues and ends with the praise. With `FLAKY=1` the step fails on its first two attempts out of every three.
Learn: `@node(retry_config=RetryConfig(max_attempts=4, initial_delay=0.2))` on a step is all it takes: ADK waits and runs the step again, so one flaky step does not end the whole conversation. Compare agent40 (retries and fallbacks around model calls) and agent47 (a retry loop you write yourself).
ADK notes that the retry count is not saved if the workflow is stopped and resumed.

## Case 6: when no route matches
Read the ADK source in `google/adk/workflow/_graph.py` (the message "The branch will end").
Expect (from the source, not run): if a node returns a route that no edge handles, that branch simply ends. A route called `DEFAULT_ROUTE` (from `google.adk.workflow`) can serve as the catch-all edge.
Learn: with a routing table, decide what happens for the case you did not think of. Here the judge's `Literal[...]` schema already limits the possible verdicts to the four routes.

## Case 7: which pattern?
| | Who decides what runs next | Good for |
|---|---|---|
| `SequentialAgent` (agent08) | you: a fixed line | steps that are always the same |
| `ParallelAgent` (agent09) | you: all at once, then combine | independent pieces |
| `LoopAgent` (agent10) | you: repeat a group of steps | "improve until good enough" |
| transfer (agent07) | the model: hands over the conversation | routing a user to a specialist |
| supervisor with `AgentTool` (agent42) | the model, step by step | work where the next step depends on the last result |
| `Workflow` graph (this agent) | YOUR code, from a verdict the model gives | branches, joins and retries you want to see and test |

Learn: the more you can draw as a fixed graph, the more predictable and testable the system is, and the fewer model calls it makes. Use a model for judging and writing, and code for deciding what happens next.

## Case 8: honest limits
Learn: 12 replies, one run each; a made-up, one-problem exercise. `Workflow` is new, and several of its features (joins that wait for several branches, running one node over many items in parallel, node timeouts, resuming after a stop) were not tried here. The routing and retry shown above are what ran.
