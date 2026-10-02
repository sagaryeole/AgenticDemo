# agent26_observability: cases, easiest first

Run: `uv run adk run agent26_observability`
Concept: observability. An agent answers with a variable number of model calls and tool calls, so "it gave a wrong answer" or "it was
slow" cannot be understood from the final text alone. You need to see what happened inside one run: which calls, how long, how many tokens.
Topic: a unit converter with two tools (`convert_length`, `convert_weight`). One question that needs both tools makes a run worth looking at.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT26_MODEL_PROVIDER` for this agent only.
Three layers, from simplest to most standard:
1. A custom plugin (always on) that prints `[trace]` lines and a run summary.
2. ADK's built-in `LoggingPlugin` (`OBS_LOGGING=1`): a detailed log of every event.
3. OpenTelemetry spans (`OBS_SPANS=1`): the standard format that tools such as Cloud Trace understand.
This agent defines `app` (the agent plus its plugins) as well as `root_agent`. `adk run` uses `app` when it is there.

## How it executes
```
 user question
      │
 ┌────▼────────────────────────── one RUN (an "invocation") ───────────────────────────────────────────┐
 │  plugin.before_run                                                                                   │
 │     │                                                                                                │
 │     ├─► model call #1  ── before_model ─► [ the model thinks ] ─► after_model    "asks for a tool"   │
 │     ├─► tool call #1   ── before_tool  ─► convert_length(...)   ─► after_tool                        │
 │     ├─► tool call #2   ── before_tool  ─► convert_weight(...)   ─► after_tool                        │
 │     ├─► model call #2  ── before_model ─► [ the model thinks ] ─► after_model    "final answer"      │
 │     ▼                                                                                                │
 │  plugin.after_run  ──► prints: 2 model calls, 2 tool calls, wall clock, % waiting for the model     │
 └──────────────────────────────────────────────────────────────────────────────────────────────────────┘
 A plugin sees ALL of this for every agent in the app. An agent callback (agent11) only sees one agent.
```

## Case 1: read the trace of one run
> How many centimetres is 3 inches, and how many kilograms is 10 pounds?

Expect (local model, from testing; Gemini gave the same structure in 2.7s):

    [trace] model call #1:   9.80s  in=  639 tok  out= 106 tok  -> asks for a tool
    [trace] tool call  #1:   0.00s  convert_length({'value': 3, 'from_unit': 'inch', 'to_unit': 'cm'}) -> {'status': 'ok', 'result': 7.62, ...}
    [trace] tool call  #2:   0.00s  convert_weight({'value': 10, 'from_unit': 'pound', 'to_unit': 'kg'}) -> {'status': 'ok', 'result': 4.5359, ...}
    [trace] model call #2:   2.18s  in=  811 tok  out=  32 tok  -> final answer
    [trace] model calls: 2 (11.98s, 1450 prompt tokens, 138 output tokens)
    [trace] tool calls : 2 (0.2 ms in tools)
    [trace] wall clock : 12.47s (96% waiting for the model)

Learn: one question became two model calls and two tool calls. Almost all the time went to the model, not to the tools. This is the
shape of a typical agent run, and it is invisible if you only look at the final reply.

## Case 2: where does the time go?
Read the numbers in case 1.
Expect: the first model call (deciding which tools to use) is slower than the second (writing the answer), and the tools take
fractions of a millisecond.
Learn: to make an agent faster you usually reduce model calls (fewer round trips, a smaller model, fewer tokens), not tool code.
Compare agent09: a parallel step helps only when it removes waiting on the model.

## Case 3: tokens grow with every call
Compare `in=639 tok` for call 1 with `in=811 tok` for call 2.
Expect: the second call sends more prompt tokens, because it carries the tool results as well.
Learn: tokens, and so cost, add up with every round trip, and long conversations make each call bigger. The model sees the whole
history on every call.

## Case 4: compare the two models
Run case 1 with `MODEL_PROVIDER=gemini` and with `MODEL_PROVIDER=local`.
Expect: the same two-model-call, two-tool-call structure, with different times and token counts.
Learn: observability makes comparisons concrete. "Gemini is faster" becomes "model call #1 took X seconds instead of Y".

## Case 5: tool calls versus model calls
Ask something that needs many conversions: "Convert every whole number of inches from 1 to 6 into centimetres."
Expect (Gemini, from testing): `model calls: 2` and `tool calls: 6`, with all six `convert_length` calls listed after model call #1.
Gemini asked for all six conversions in ONE response, so it needed only two model calls. A model that asks for one tool at a time would need
seven model calls for the same job, and the summary would show it.
Learn: the two numbers tell you how the agent worked. Many tool calls in one round trip is cheap. Many model calls is slow and costly,
and a number that keeps growing is the early warning for a loop going in circles (compare agent24, where a thinking-off model made 20+
checking calls). In production you would alert on it. (The same question on the local model was not measured.)

## Case 6: the standard format, OpenTelemetry spans
    OBS_SPANS=1 uv run adk run agent26_observability

Expect: lines such as (local model, one conversion):

    [span]   4387.6 ms  generate_content openai/qwen3.5-9b  {...}
    [span]      0.7 ms  execute_tool convert_length         {'gen_ai.tool.name': 'convert_length', ...}
    [span]   4394.4 ms  call_llm                            {...}
    [span]   1221.5 ms  generate_content openai/qwen3.5-9b  {...}
    [span]   6080.4 ms  invoke_agent root_agent             {...}
    [span]   6082.9 ms  invocation                          {}

Learn: a span is a timed record. Spans nest: `generate_content` happens inside `call_llm`, which happens inside `invoke_agent`, which
happens inside the whole `invocation`. They print when they finish, so inner ones come first. ADK creates these spans on its own; the
file `spans.py` only adds a tiny exporter that prints them. A real exporter sends them to a backend (such as Cloud Trace) where you
see the same tree as a chart. That step needs cloud setup and was not run here.

## Case 7: ADK's built-in logging plugin
    OBS_LOGGING=1 uv run adk run agent26_observability

Expect: many grey `[logging_plugin]` lines: USER MESSAGE RECEIVED, INVOCATION STARTING, AGENT STARTING, LLM REQUEST, and so on, with
the details of each step.
Learn: for a quick look at everything that happens, a ready-made plugin is enough. Writing your own plugin (case 1) is for exactly the
numbers you care about.

## Case 8: write your own measurement
Open `RunSummaryPlugin` in `agent.py`. Add a counter for tool errors: in `after_tool_callback`, check `result.get("status") == "error"` and
count it, then print it in `after_run_callback`. Ask for a conversion with a unit the tool does not know ("2 parsecs in cm").
Learn: a plugin is a small class with a few methods. You can count whatever matters to you: errors, tokens per user, slow calls.

## Case 9: three tools for three jobs
| | Plugin (case 1) | Logging plugin (case 7) | Spans (case 6) |
|---|---|---|---|
| Shows | the numbers you chose | everything, as text | timed tree of calls |
| Effort | a small class | one line | exporter and a backend |
| Good for | dashboards and alerts | debugging one run | production tracing across services |

Learn: start with the plugin or the logging plugin while building. Add spans when you need to follow requests across several services.
