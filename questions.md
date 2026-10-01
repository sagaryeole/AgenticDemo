## What is an agent, precisely?
Not a single LLM call. It's an LLM in a loop with three things: an instruction (system prompt defining role/constraints), a set of tools it can choose to invoke, and a runner that manages that loop until the model decides it has enough information to answer. The key distinction from a chatbot: the model decides whether and when to call a tool — you don't hardcode the sequence.

## The agent loop (what you saw in your trace):

User message enters
Model receives instruction + message + tool schemas
Model either answers directly, or emits a function_call
Runner executes the actual Python function, gets a result
Result goes back to the model as a function_response
Model produces a final answer (or calls another tool — this can repeat)

This loop is why observability of agents is different from observability of normal APIs: a single user request can trigger a variable number of model calls and tool calls, so your tracing has to capture the whole chain, not just one request/response pair. That's your bridge into tomorrow and Day 4.

## Tool calling / function calling:
The model doesn't execute your Python function — it never runs your code directly. It sees your function's name, docstring, and type-hinted parameters (ADK converts these into a JSON schema), and outputs a request to call it with specific arguments. ADK's runner intercepts that request, actually executes your Python function, and feeds the result back in. This is why your docstring quality mattered yesterday — it's not documentation, it's literally the interface contract the model reads to decide when and how to call the tool.

## Grounding vs. hallucination — the concept you actually tested today:
Grounding means the model's answer is derived from retrieved/tool data rather than from its training-time knowledge. Your orders-api test showed partial grounding: the "no errors" statement was grounded (came straight from tool output), but the "possible upstream/gateway issue" reasoning was the model's own inference, stylistically indistinguishable from the grounded part until you added labeling instructions. This is the core evaluation problem in production agents — an ungrounded but plausible-sounding statement is more dangerous than an obviously wrong one, because it's harder to catch.

## Session and state:
Each conversation is a Session (you saw the SQLite session.db get created). This is what lets an agent hold multi-turn context — the "explain more about that timeout" follow-up works because prior turns are stored and replayed into context, not because the model "remembers" across calls. Statelessness-by-default with explicit session storage is the same mental model as a web session store — familiar territory for you from ordinary backend work.

## adk run vs adk web:
adk run is a raw stdin/stdout loop — good for scripting and quick checks. adk web runs a local API server plus a debugging UI, and it's the one that matters for this interview track because it exposes the trace/event view — the same signal an observability system would capture in production, just visualized locally instead of shipped to Cloud Trace.

## One likely interview question from today's material:
"How do you prevent an agent from hallucinating when tool data is empty or insufficient?" Your honest answer, backed by a real test: constrain the instruction to explicitly separate tool-grounded statements from model speculation, and label the speculation. Don't claim you solved hallucination — no one has. Claim you made the boundary between fact and inference visible, which is the realistic, defensible framing.

---

# Learnings from agents 01-13

Each section below comes from something that was actually run in this repo. The agent folder is named
so you can reproduce it.

## Who decides what runs next? (the one table to remember)

| Pattern | Agent | Who decides the path | Use it when |
|---|---|---|---|
| Single LLM agent with tools | 02, 04, 05 | the LLM, each turn | open-ended questions |
| Coordinator + sub-agents | 07 | the LLM, by reading sub-agent descriptions | the path depends on the request |
| `SequentialAgent` | 08 | your code, fixed order | the steps are always the same chain |
| `ParallelAgent` | 09 | your code, all at once | sub-tasks are independent |
| `LoopAgent` | 10 | your code repeats; a stop signal or `max_iterations` ends it | "draft, check, revise until good" |

Workflow agents (08-10) contain no LLM of their own. They are plain control flow around LLM agents, and they
nest: agent09 is a `SequentialAgent` whose first step is a `ParallelAgent`.

## The model is swappable; the agent design is not tied to it (agents 03, 07)
ADK talks to Gemini natively (model given as a plain string) and to other models through LiteLLM. LM Studio exposes an
OpenAI-compatible server, so the model string is `openai/<id>`: `openai/` picks the protocol, `<id>` must match
the id LM Studio reports, and `api_base` points at `http://127.0.0.1:1234/v1`. The first bug in this repo was a
truncated `api_base` (`http://127.0.0.1` without the port and `/v1`). `common/models.py` turns the choice into one
environment variable (`MODEL_PROVIDER`), with a per-agent override. Built-in tools are the exception: `google_search`
is a Gemini feature and does not move to a local model.

## Configuration: where does `.env` come from?
ADK searches for `.env` starting in the agent's folder and walking up through parent folders, and uses the first
one it finds. So one root `.env` serves every agent unless a folder has its own. A fresh clone with no `.env`
fails with "No API key was provided" for every Gemini agent: the error is about missing config, not a code bug.
Real environment variables set on the command line win over `.env` values.

## Small local models: what to expect (agents 03-06, and 07+ on local)
A 9B local model handled single tool calls, state, structured output and simple routing well. It was weaker at:
counting (it said "5 words exceeds the limit of 6"), calling a tool every round of a loop (after the first round it
copied its own earlier rejection instead of calling the tool again), and strict judgement. Design for that: move
anything code can check into code, and give the model one decision at a time.

## State is the glue between turns and between agents (agents 05, 06, 08-10)
`tool_context.state` (in tools) and `callback_context.state` (in callbacks) is a per-session dict. It survives
across turns in the same session and starts empty in a new one. `output_key="x"` saves an agent's reply into
`state["x"]`, and `{x}` in a later agent's instruction is replaced with it. `{x?}` means "if it exists", which is
how agent10's writer works in round 1 before any feedback exists. Parallel branches must write to different keys,
or one overwrites the other. When you change a list in state, reassign it (`state["notes"] = notes`) so ADK
records the change.

## Structured output guarantees the shape, not the truth (agent06)
`output_schema` (a Pydantic model) forces JSON with the right fields, and `Literal[...]` restricts values to a
fixed set. Every reply was valid JSON. One was still wrong: "does this phone case fit the older model?" was given
the topic "quality" because none of the allowed topics fit and the model picked the closest. Give every `Literal` an
honest "other". In this ADK version `output_schema` and tools can be
combined: tools run during the reasoning loop and only the final answer is forced into the schema. (Older ADK
versions and many tutorials say the opposite, that a schema disables tools. Check the docstring of the version
you use.)

## Multi-agent transfer: the LLM routes, and the specialist keeps the floor (agent07)
The coordinator picks a sub-agent by reading the sub-agents' `description` fields, so descriptions are routing
rules. After a transfer the specialist answers the following turns too: after a currency question, "what is a
passport?" was answered by `currency_agent`, while in a fresh session the coordinator answered it. A two-part
question was answered by chained hand-offs, with the second agent repeating the first. Transfer is flexible but
not tidy. When the steps are known in advance, use a workflow agent instead.

## Loops need a stop condition you trust, and a cap (agent10)
A `LoopAgent` stops when a step yields an event with `escalate=True`, or at `max_iterations`.
This agent took three designs to get right, and each failure is a lesson:
1. An LLM critic that counted words: it miscounted ("5 words exceeds the limit of 6").
2. An LLM critic with a tool that checked the rules: on the local model it called the tool in round 1, then in
   later rounds copied its earlier rejection without calling it, so the loop ran to the cap. Even when the rules
   were in code, the model could still skip the call.
3. A plain-Python `BaseAgent` as the checker, with no model at all. In testing it ended on a correct approval in
   every run, on both Gemini and the local model.

Also: a judgement the model made ("does it name the product?") was lenient. Gemini approved "We Keep You Rolling."
for a bicycle repair shop. Replacing it with a code rule (contains a product word) fixed that, though the rule is
only as smart as you write it: "Know Your True Worth." still passes for a net worth calculator.
Rule: code for checkable rules, a model only for real judgement, and always set `max_iterations`. A workflow step
does not have to be an LLM.

## Guardrails are callbacks at fixed checkpoints (agent11)
- `before_model_callback`: return a reply to skip the model. Used to stop card numbers ever reaching the model.
- `before_tool_callback`: return a result to skip the tool. Used to reject "500 pizzas", an argument the model chose.
- `after_model_callback`: replace the reply. Used to remove internal email and phone details.

Lessons: a guardrail is a net, not a wall. The "not on the menu" check never fired because both models read the
menu and refused on their own; it is there for when they don't. Pattern checks can be dodged (a card number in
words). This guard only checks the newest message, so earlier sensitive text stays in the history. When a model
refused something the guardrail missed, that was the model's choice, not your control.

## MCP: tools that live outside the agent (agent12)
`McpToolset` starts an MCP server as a separate process, asks it for its tool list at startup, and forwards
calls to it. The agent file contains no tool code, so a tool added to the server is usable without changing the
agent. `tool_filter` limits which server tools the model sees. Version note: the `mcp` 2.x package renamed
`FastMCP` to `MCPServer`, so most online examples are out of date.

## When the model is wrong, check the tool first (agent12)
The catalogue tool `list_books` did not return availability, and the instruction asked for it. Gemini answered
"Available" for every book, including one that was not. Nothing was wrong with the prompt; the information was
missing, so the model filled the gap. The fix was in the tool (return the field). This is the same grounding
problem as the orders-api test above, caused by data instead of instructions.

## Evals: test the action and the answer separately (agent13)
`adk eval` replays written cases against the real agent. Two checks matter:
- Trajectory (`tool_trajectory_avg_score`): did it call the right tool with exactly the right arguments?
- Response: does the answer match a reference?

Findings: the word-overlap metric (`response_match_score`, ROUGE) passed a reference answer that said the
opposite ("is available" vs "is not available") at 0.89. The LLM-judge metric (`final_response_match_v2`)
failed it at 0.0. Reintroducing the agent12 bug was caught on both models but differently: Gemini gave a wrong
answer (judge failed), the local model found another route via `get_book` and was right (trajectory failed).
A failing eval says "something changed"; read the details before deciding it is a bug. An expectation can also be
wrong: expecting `"J.R.R. Tolkien"` as the argument failed 3 of 3 runs because the question said "Tolkien".

## More likely interview questions, with answers backed by this repo
- "When would you use a workflow agent instead of letting the LLM orchestrate?" When the steps are known.
  Agent07's LLM routing handled a two-part request with messy chained hand-offs; agent08's `SequentialAgent`
  runs the same steps in the same order every time.
- "How do you stop an agent loop from running forever?" A trusted stop signal plus `max_iterations`. Show agent10:
  a model-driven exit failed on a small model, a code-driven exit fixed it, and the cap is the backstop.
- "How do you keep sensitive data away from the model?" A `before_model_callback` that blocks before the call,
  and be honest about its limits (pattern dodges, history not rechecked).
- "How do you know your agent still works after changing the prompt or the model?" An eval set with trajectory
  and judge metrics, run on every change. Mention that ROUGE missed a meaning flip and the judge caught it.
- "Why did your agent state something false?" Check whether the tool returned that information before blaming
  the model (agent12).
- "What changes when you move to a small local model?" Less reliable counting, tool chaining and judgement;
  keep decisions small and push checkable rules into code.