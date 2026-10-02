# agent38_many_tools: cases, easiest first

Concept: what changes when an agent has MANY tools. Every tool's name, description and arguments are sent to the model with every request. With 3 tools that is nothing. With 20, 50 or 200 it
costs tokens on every call, and the model has more look-alike tools to confuse. Three things to try: write good descriptions, give the model fewer tools, or choose the few tools that fit the message.
Topic: a study helper with 20 small tools in `tools.py`: four unit converters (length, temperature, weight, money), two percentage tools, `average`, `split_bill`, three date tools (`days_between`,
`add_days`, `weekday_of`), two text-length tools (`count_words`, `reading_time`), two text tools, three random tools and two number tools. Several are close neighbours on purpose.
Run: `uv run adk run agent38_many_tools` (set `TOOL_MODE` first, see below), and the measurement `tool_choice_test.py`, which asks 24 questions in fresh sessions and checks which tool was called FIRST:

    TOOL_MODE=all    uv run python agent38_many_tools/tool_choice_test.py
    TOOL_MODE=vague  uv run python agent38_many_tools/tool_choice_test.py
    TOOL_MODE=routed uv run python agent38_many_tools/tool_choice_test.py     (TOP_N=4 tools offered by default)

Add `MODEL_PROVIDER=local` in front for the local model. Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT38_MODEL_PROVIDER` for this agent only.
Embeddings (for `routed`) follow the chat provider unless `EMBEDDING_PROVIDER` is set. The agent prints `[tool call] ...`, `[routing] offered: [...]` and `[tool error] ...` lines.

| `TOOL_MODE` | What the model is given |
|---|---|
| `all` (default) | all 20 tools with proper descriptions |
| `vague` | all 20 tools, but every description replaced by "A helper function." (the names stay) |
| `routed` | only the `TOP_N` tools whose description is closest in meaning to the user's message (embeddings, labs 17-18) |

## How it executes
```
 MODE all / vague                                      MODE routed
 user: "What date is 45 days after 2026-01-10?"        user: "What date is 45 days after 2026-01-10?"
        │                                                     │
        ▼                                                     ▼
 request to the model carries ALL 20 tool                NearestTools.get_tools(...)   ADK asks the toolset before EVERY model call
 declarations (names, descriptions, arguments)             embed the message, cosine against the 20 tool descriptions ► keep the 4 closest
        │                                                     │   [routing] offered: [add_days, days_between, weekday_of, percentage_of]
        ▼                                                     ▼
 LLM picks one:  add_days(start_date, days)              request carries only those 4 declarations
                                                              │
                                                              ▼
                                                       LLM picks one:  add_days(...)
```

## Case 1: all 20 tools
Run the test with `TOOL_MODE=all`. Expect (from testing, 24 questions): the first tool was right 24 of 24, on both models. Average prompt tokens of the first model call: local 3,014, Gemini 980,
and 0 failed tool calls.
Learn: a model handles 20 clearly described tools without trouble, even look-alikes such as `days_between` and `add_days`. The cost is in the prompt: the tool declarations are most of those tokens.
(Token counts come from each service, which counts differently. Compare the modes of one provider with each other, not the two providers.)

## Case 2: vague descriptions
Run with `TOOL_MODE=vague`. Expect (from testing): the first tool was still right 24 of 24, but 6 tool calls failed on the local model and 8 on Gemini, for example
`convert_length: KeyError: 'kilometres'`, `convert_weight: KeyError: 'pounds'`. Prompt tokens fell to 2,273 (local) and 234 (Gemini).
Learn: the NAMES alone were enough to choose the tool. What the missing descriptions took away was the ARGUMENT rules: "Converts a length between units: mm, cm, m, km, inch, ft, mile" tells the model to write `km`,
and with "A helper function." it wrote `kilometres`, and the tool failed. Descriptions guard the arguments more than the choice. The failure did not crash the run: `on_tool_error_callback` in `agent.py`
turned it into an error result that goes back to the model (agent32 has the same callback). Without it, the first `KeyError` stopped the whole test.

## Case 3: fewer tools, chosen by meaning (routed)
Run with `TOOL_MODE=routed`. Expect (from testing): first tool right 24 of 24 again, and prompt tokens down to 802 (local, from 3,014) and 284 (Gemini, from 980), about 70 percent fewer. 0 failed tool calls.
Learn: `NearestTools` in `agent.py` is a toolset. ADK asks a toolset for its tools before every model call, so it can look at the user's message and offer only the best matches. The model cannot choose a tool it is not shown,
so the 16 irrelevant tools cannot be picked by mistake and do not cost tokens. This is retrieval (agent19) applied to TOOLS instead of documents.

## Case 4: the risk of routing
Run `TOP_N=1 TOOL_MODE=routed MODEL_PROVIDER=local ...` and then `TOP_N=2`.
Expect (from testing, local): 23 of 24 both times. "What date is 45 days after 2026-01-10?" went to `weekday_of` (with 1 tool offered) or `days_between` (with 2), and 446 / 552 tokens.
Learn: if the right tool is not among the ones offered, the model cannot call it, and it may use a wrong one instead. Offer enough tools to include the right one (here 4 was enough for all 24 questions) and measure
your own questions: look at the `[routing] offered:` line for the question that failed.

## Case 5: what does the model see?
Run `TOOL_MODE=routed uv run adk run agent38_many_tools` and type: "Pick a number between 1 and 50." Then "Make 'study hard' all capital letters."
Expect (not run by hand, reasoning only): a different `[routing] offered:` list for each message (random tools first, then text tools).
Learn: the tool list is rebuilt for every request. A follow-up that needs a different kind of tool gets different tools.

## Case 6: not tested here
Try these yourself. (a) 60 tools instead of 20 (copy a few converters): do the vague and the routed rows move more? Twenty well-named tools were not enough to confuse either model, so the gap probably
shows at larger sizes. (b) `tool_filter=[...]`, a list of allowed tool names that ADK toolsets accept, for a fixed subset. (c) Another way to cut tools: group them into sub-agents (agent07), so each agent has 5 tools and a coordinator
picks the agent.
Learn: the choices differ in who decides which tools are visible: you (a fixed filter), the message (routing), or a coordinator agent (sub-agents).

## Case 7: honest limits
Learn: 24 questions, one run each. "24 of 24" means the questions were not hard enough to separate the modes on tool CHOICE; the reliable differences are tokens (about 70 percent saved by routing) and failed calls (vague descriptions).
The questions are short and clearly worded; real users write messy ones.
