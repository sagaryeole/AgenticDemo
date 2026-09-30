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