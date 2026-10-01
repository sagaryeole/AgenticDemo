# agent04_localmodelwithtool: cases, easiest first

Run: `uv run adk run agent04_localmodelwithtool` (LM Studio server must be running).
Concept: a custom Python function as a tool, on a local model.

## How it executes
Control: the LLM decides whether to call the tool. ADK runs the function, not the model.

```
 user message
      │
      ▼
 ┌──────────┐  no tool needed   ┌──────────────┐
 │ local    ├──────────────────►│ final answer │
 │ LLM      │                   └──────────────┘
 └────┬─────┘                           ▲
      │ function_call                   │
      │ get_current_time("Europe/Stockholm")
      ▼                                 │
 ADK runs your Python function          │
      │ function_response               │
      └────────────► local LLM ─────────┘
```

## Case 1: tool needed
> What time is it in Stockholm right now?

Expect: `get_current_time` is called with timezone `Europe/Stockholm` and the answer matches your clock.
Learn: ADK turns the function's name, type hints and docstring into the tool schema.

## Case 2: tool not needed
> What is the capital of France?

Expect: a direct answer, no tool call.
Learn: the model chooses. The instruction only says when to use the tool.

## Case 3: argument filled from the question
> And what about Tokyo?

Expect: timezone `Asia/Tokyo`.
Learn: the model maps a city to an IANA name using the docstring examples.

## Case 4: invalid input, with or without the tool
> What time is it in Atlantis?

Expect: either of two outcomes, and neither shows an invented time.
- The model skips the tool and says Atlantis is not a real place (what `qwen3.5-9b` did in testing).
- The model calls the tool, gets `Unknown timezone`, and reports the error.
Learn: the model may reject bad input before any tool call. To test the tool's error path
directly, ask for a real city with a bad zone name: "What time is it in the timezone Mars/Olympus?"

## Case 5: a small model may skip the tool
Ask the same question five times in new sessions.
Expect: usually a tool call, sometimes a guess from the model.
Learn: local models are less reliable at function calling. Test them before depending on them.
