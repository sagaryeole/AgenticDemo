# agent02_toolcall: cases, easiest first

Run: `uv run adk run agent02_toolcall` (needs Vertex AI / GCP login, see README).
Concept: a built-in tool (`google_search`) the model can choose to call.

## How it executes
Control: the LLM decides, per message, whether to call the tool.

```
 user message
      │
      ▼
 ┌──────────┐   needs no tool   ┌──────────────┐
 │   LLM    ├──────────────────►│ final answer │
 └────┬─────┘                   └──────────────┘
      │ needs fresh info                ▲
      ▼                                 │
 google_search ──► results ──► LLM ─────┘
 (runs outside the model)     (may search again)
```

## Case 1: no tool needed
> What does HTTP status 404 mean?

Expect: a direct answer, no search.
Learn: the model decides whether to use a tool. You don't hardcode it.

## Case 2: tool needed for fresh information
> What is the latest stable version of Python?

Expect: a search happens (see the trace in `adk web`) and the answer cites it.
Learn: tools give the model facts it cannot know from training.

## Case 3: compare with agent01
Ask agent01 and agent02 the same question from case 2.
Expect: agent01 answers from training data, possibly out of date. agent02 searches.
Learn: this is the difference between ungrounded and grounded answers.

## Case 4: watch the loop in adk web
Run `uv run adk web`, ask case 2 again, open the Trace/Events view.
Expect: user message, function call, function response, final answer.
Learn: this is the agent loop from questions.md. One request can mean several model calls.

## Case 5: a limit of built-in tools
`google_search` is a Gemini feature. Copy this agent to a local model and it fails.
Learn: built-in tools depend on the model. This motivates agent03 and agent04.
