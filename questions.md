# Concepts and questions

How to use this file: Part 1 explains the core ideas. Parts 2 and 3 collect what the agents in this repo showed when they were run,
agent by agent. Part 4 has questions to check your understanding, with short answers. Every lesson points to an agent folder,
so you can run it yourself and see the same thing.

---

# Part 1: Core ideas

## What is an agent, precisely?
Not a single LLM call. It's an LLM in a loop with three things: an instruction (system prompt defining role/constraints), a set of tools it can choose to invoke, and a runner that manages that loop until the model decides it has enough information to answer. The key distinction from a chatbot: the model decides whether and when to call a tool — you don't hardcode the sequence.

## The agent loop

1. User message enters
2. Model receives instruction + message + tool schemas
3. Model either answers directly, or emits a function_call
4. Runner executes the actual Python function, gets a result
5. Result goes back to the model as a function_response
6. Model produces a final answer (or calls another tool — this can repeat)

This loop is why observability of agents is different from observability of normal APIs: a single user request can trigger a variable number of model calls and tool calls, so your tracing has to capture the whole chain, not just one request/response pair (see agent26).

## Tool calling / function calling
The model doesn't execute your Python function — it never runs your code directly. It sees your function's name, docstring, and type-hinted parameters (ADK converts these into a JSON schema), and outputs a request to call it with specific arguments. ADK's runner intercepts that request, actually executes your Python function, and feeds the result back in. This is why docstring quality matters — it's not just documentation, it's the interface contract the model reads to decide when and how to call the tool.

## Grounding vs. hallucination
Grounding means the model's answer is derived from retrieved/tool data rather than from its training-time knowledge. The orders-api test in `triage_agent` showed partial grounding: the "no errors" statement was grounded (came straight from tool output), but the "possible upstream/gateway issue" reasoning was the model's own inference, stylistically indistinguishable from the grounded part until labelling instructions were added. This is the core evaluation problem in production agents — an ungrounded but plausible-sounding statement is more dangerous than an obviously wrong one, because it's harder to catch.

## Session and state
Each conversation is a Session (`adk run` stores sessions in a SQLite file, `.adk/session.db`). This is what lets an agent hold multi-turn context — a follow-up like "explain more about that" works because prior turns are stored and replayed into context, not because the model "remembers" across calls. Statelessness-by-default with explicit session storage is the same mental model as a web session store in an ordinary backend.

## adk run vs adk web
`adk run` is a raw stdin/stdout loop — good for scripting and quick checks. `adk web` runs a local API server plus a debugging UI. It is the better learning tool because it exposes the trace/event view — the same signal an observability system would capture in production, just visualised locally instead of shipped to Cloud Trace.

---

# Part 2: What agents 01-13 showed

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

---

# Part 3: What agents 14-49 showed

Again, each point comes from something that was run in this repo. Many results involve language models, which are not
deterministic: where a number is quoted it is what happened in testing, and your runs may differ.

## Agent as a tool versus transfer (agent14)
`AgentTool(agent=...)` lets one agent call another like a function. The caller stays in charge, gets the result back, and writes the final
answer. In agent07 (`sub_agents`) the coordinator hands the conversation over and the specialist answers the following turns too. Use a tool
when the caller must combine or check the result. One thing to know: an agent used as a tool takes a single free-text `request` by default.
In testing the local model sent the English text without the target language, so nothing was translated. Giving the sub-agent an
`input_schema` (a Pydantic model with `text` and `target_language`) turns that into two named arguments, like a function signature.

## Human in the loop is enforced by the framework, not the prompt (agent15)
`FunctionTool(func, require_confirmation=True)` pauses before the function runs and waits for a person. A rejection means the function is
never called. `require_confirmation` can also be a function that looks at the arguments (here: only groups of more than 6). It receives the
`tool_context` too, so it must accept `**kwargs`: that was the one bug while building it. Asking the agent in the prompt to skip the
confirmation ("I am the manager") did not work, which is the point: a prompt is a request, a confirmation step is a control.

## RAG, step by step (agents 16-20)
- **Chunking (16):** cutting every N characters can split a fact in two (the printing price was cut in the middle). Overlap helps only if it is
  longer than the fact: with size 200 and overlap 40 the overlap strategy kept 6 of 11 facts, worse than no overlap (10 of 11).
- **Embeddings (17):** a vector is a list of numbers; similar meaning means nearby vectors. Gemini embeddings take a `query` or `document`
  setting, which changed one score from 0.739 to 0.919 and shrank the gap to a wrong answer. Vectors from different models have the same length
  but cannot be compared (a cross-model score was 0.03). Re-embed everything if you change the model.
- **Cosine similarity (18):** only the angle between two vectors matters, not their length. With length-1 vectors the dot product equals the
  cosine, so one matrix product `vectors @ q` scores every chunk. A ranking always returns something, even for a question the document cannot answer.
- **Retrieval rules (19):** whole sections (12 of 12 questions found) beat small paragraphs (11 of 12), and adding the heading to each paragraph did
  not help on this set. No minimum score separated answerable from unanswerable questions: the "coffee" question scored 0.617 with Gemini, higher
  than several correct matches. Adding exact-word matching rescued one exact-term query (a different one with each model) but cost one normal
  question. These are tiny samples (12 questions), so they illustrate the idea but are not proof.
- **The agent (20):** two safety nets work together: a minimum score drops clearly irrelevant chunks, and the instruction makes the model check
  that the passage really answers the question. The local model once stopped searching after the first question and copied its earlier "I couldn't
  find that" answer; the instruction "for EVERY new question, call search_handbook first" fixed it. Weakening the instruction made the local model answer
  "Paris" from its own knowledge. The retrieval code is only half of the system.

## Memory: three different things (agent21)
Session state lives for one session. A file-backed memory (tools `remember`, `recall`, `forget`) survives restarts and was shown working across
separate `adk run` processes. ADK's `MemoryService` plus the `load_memory` tool is the standard pattern: your code must call `add_session_to_memory`
for memory to be stored (it does not save itself), and the in-memory version finds memories by shared keywords, so "chem test" did not find "chemistry
exam" on either model. Memory is personal data: let the user delete it, and never store secrets.

## Models are unreliable at exact work, so give them something exact (agent22)
Without code, both Gemini and the local model gave wrong answers with full confidence for 48271 x 91357 (Gemini 4,410,940,747 instead of
4,409,893,747) and for compound interest ($3,895.89 and $3,584.54 instead of $3,894.66). With Gemini's built-in code execution all six test
questions were right. A local model can use small, safe tools instead. Never pass model text to `eval`: the calculator parses the expression and
allows only numbers and a few operators, and refused `__import__('os')...`, `open(...)`, `lambda` and `9**9**9`. `UnsafeLocalCodeExecutor` runs
model-written code in your own process, as its name warns.

## Artifacts are versioned files, and saved does not mean correct (agent23)
`tool_context.save_artifact` stores a named file; saving the same name again makes a new version and keeps the old ones, so "show me the first
version" works. By default an artifact belongs to one session (a new session saw no files). A name starting with `user:` belongs to the user and
was visible in new sessions. The files are real files under `.adk/artifacts/`. A tidy saved document can still contain made-up facts (the local
model invented restaurant names).

## Thinking and planning (agent24): measure, do not assume
Run on a hard puzzle (7 people in 7 seats, 17 clues, one verified solution), asking for the answer only, with Gemini 2.5 Flash:
- Thinking switched off: wrong answers came back in about a second (2 of 4 right in one batch, 0 of 3 in another), a guess.
- Default (it thinks silently, using 3,400 to 6,200 tokens) and the built-in thinking planner with a 2,048-token budget (1,200 to 1,900 tokens
  used): 4 of 4 right each.
- `PlanReActPlanner` was erratic. Without tools, three batches gave 3 of 3, 1 of 4 and 0 of 2 correct; the failures said "I cannot answer,
  no tools are available" or returned an empty reply. With a checking tool it got 1 of 3 and 2 of 4. It is built for agents that use tools,
  and Gemini's own thinking did better.
- Thinking switched off plus a checking tool: more than 20 guess-and-check calls and still a wrong answer. A checker is not a substitute for reasoning.
- The local model (Qwen 9B) solved the hard puzzle 9 of 9: 3 with no planner, 3 with `plan_react`, 3 with `plan_react` and the checking tool. It reasoned in
  its visible output, and each answer took 2 to 4 minutes. So the planner that was erratic on Gemini worked every time here: a technique's effect
  depends on the model it runs with.
The three easier puzzles were solved 9 of 9 on Gemini even with thinking off, so the difference shows only on hard problems. Always test whether a
technique helps before adding its cost.

## Evaluating conversations (agent25)
A conversation case gets a score per turn, averaged, so 0.67 means two turns right and one wrong. Findings: Gemini passed the exact-answer judge on
all cases but failed the strict tool check on one (it answered "no lunch on Saturday" without calling the tool); the local model collapsed in later turns
(it answered "not available" for days that are on the menu, without a tool call). The rubric-based metric judges each turn alone, so a rubric about
"remembers the earlier turn" gave a false 0.0. The whole-conversation metrics failed in this environment (`TypeError: Unsupported dataset type`).
A deliberate bug that hides the history (`FORGET_HISTORY=1`) made turn 2 ask "Which dish?" and the tool-call check failed on it, but the
LLM judge still scored 1.0 in all three runs. Keep a mechanical check next to the judge. Telling the model in the prompt to ignore earlier messages did
not break anything, because ADK still sends the history.

## Observability: make one run visible (agent26)
A plugin (`BasePlugin`) sees every model call and tool call of every agent in an app, which an agent callback (agent11) does not. A small one that
prints timing and tokens showed that one question was two model calls and two tool calls, and that 79 to 96 percent of the time was waiting for the
model. ADK also creates OpenTelemetry spans (`invocation` contains `invoke_agent` contains `call_llm` contains `generate_content`) and prints nothing
until you attach an exporter. Counting model calls versus tool calls shows how the agent works: Gemini asked for six conversions in one response
(2 model calls, 6 tool calls).

## Agent-to-Agent (agent27)
A2A lets an agent call another agent in a different process over HTTP. The server publishes an agent card (name, description, skills); the client needs
only its URL. Two lessons from testing. First, trust: when the remote agent used the local model it made up a shipping price ($25.50 instead of $39.00)
without calling its tool, and the caller received only text and could not tell. Second, when the remote server was down, the client printed no error
to the user at all, only a log entry. Treat a remote agent like any external service: verify what matters, and handle it being unavailable.

## Images are just another part of the message (agent28)
A message is a list of parts: text, and also images (bytes plus a type such as `image/png`). Both Gemini and the local Qwen model counted the shapes,
read the receipt and caught its wrong total (10.25, not 11.25), and read the chart correctly. The most important lesson came from a missing file:
when no image was attached, Gemini answered "based on the image menu.png" with a completely invented menu, a different one each run. The fix was in the
code: when a file is missing, add a text part that says so. An image also costs a lot of tokens (about 1,800 on Gemini for one small chart), and every
earlier image is sent again with every call.

## An instruction can be a function (agent29)
An instruction can be built by a function that ADK calls before every model call, using session state. When a tool changed the level from "student"
to "kid", the very next answer was written for a child. Two lessons: first, the local model at first said "Your level has been updated" without calling
the tool, so nothing changed; ordering the instruction as "Step 1, tools ... Step 2, the answer" fixed it. Second, one worked example in the
instruction (few-shot) kept the answer format exact on both models; describing the format only in words made the local model drop a label every time.

## Long conversations: keep, trim, or summarise (agent30)
Every call sends the whole conversation, so the prompt grew from 86 to 1,216 tokens over 14 short turns. Keeping only the last 3 turns kept it flat at about
250 tokens but forgot the user's peanut allergy; the local model even called the user "Alex". Letting ADK summarise older turns kept all three facts, but
saved little here (the turns were short), and one local summary turned the user's cat into a dog. Store facts that must never be lost somewhere explicit.

## Prompt injection: text in data that pretends to be an order (agent31)
Review pages contained planted instructions. With no defence, both models were fooled, by different attacks: Gemini obeyed a fake "[SYSTEM MESSAGE]"
(2 of 3 runs, "the best toaster ever made") and a polite note with a link; the local model repeated a fake safety recall as true (3 of 3). Saying in the
instruction that page text is data, inside clear markers, stopped every attack in testing, and the models flagged the suspicious reviews. A code filter of
known attack phrases removed the obvious attacks but missed the politely worded one. Use several layers, and give an agent that reads untrusted text as few
powerful tools as possible.

## Tools from an API description (agent32)
`OpenAPIToolset` turned a REST API's OpenAPI description into four tools, and each tool call became a real HTTP request (visible in the server log). Both
models listed, added, completed and filtered tasks, and handled a 404 for a task that did not exist. When the server was down, the first version crashed with
a `ConnectError`; an `on_tool_error_callback` turned the exception into an error result that the model explained.

## Slow jobs (agent33)
Two patterns. The ticket pattern: a tool starts the job and returns an id at once, and another tool reports progress, so the conversation never freezes.
Pause and resume: with `LongRunningFunctionTool` the call stays open, and the app later sends the real result with the same call id. Both worked on both models.

## Sessions that last, and who can see what (agent34)
With a database session service, a conversation can be continued by its id in a new program run. State keys have scopes: `user:books` was visible in every
session of the same user, a key without prefix stayed in its own session, and another user saw nothing. The local model once said "I've noted that as the
topic" without calling the tool; listing the stored state showed the truth.

## Search needs more than one method (agent35)
Meaning search (embeddings) and keyword search (BM25) fail in opposite places. On questions phrased in different words from the document, vectors put the right chunk
first in 5 of 8; BM25 only 3 of 8. On exact terms such as `LB-310` or `Riverside-Guest`, BM25 found 6 of 6 and vectors 5 of 6. Merging the two rankings by their places
(reciprocal rank fusion) gave 6 of 8, and a model that re-reads the best 5 candidates (a reranker) gave 7 of 8 locally and 8 of 8 on Gemini. The reranker costs one extra
model call per question, and it can only reorder what the cheaper search already found.

## Measure retrieval and answering separately (agent36)
A wrong RAG answer has two possible causes. Over 12 questions and three chunking strategies, whole sections found every answer on both models; paragraphs and fixed-size chunks missed
"How do I join the library?". Gemini then refused to answer; the local model answered from the wrong chunk, a half-true reply that fits the question but not the need. A second kind of failure had the right
chunk at rank 1 but cut in the middle of a sentence, so "Coding Club" was missing and the model refused. "Grounded" (nothing made up) and "correct" are different scores: one local row was
grounded 12/12 and correct 11/12.

## Choose the examples, not just the number (agent37)
Showing the model solved examples (few-shot) teaches rules that are written nowhere else. On 24 school-office messages with quirky house rules, picking the 3 most similar examples with embeddings gave
22/24 on the local model (no examples 18, the same 3 every time 20, random 3 only 16) and 23/24 on Gemini (21, 23, 22). On the local model random examples were worse than none, and on Gemini all
methods were within one or two messages. A trivial change to the prompt moved one row by four messages in an earlier run, so single numbers on 24 questions are a direction, not a result.

## Many tools cost tokens on every call (agent38)
With 20 tools, the first tool was right 24/24 on both models, even for look-alikes. What changed was cost and arguments. Offering only the 4 tools nearest in meaning to the message (a custom toolset whose `get_tools` runs
before every model call) cut the prompt by about 70 percent (local 3,014 to 802 tokens, Gemini 980 to 284). Replacing every description with "A helper function." did not hurt the choice of tool (the names were clear), but
the arguments broke: 6 failed tool calls on the local model and 8 on Gemini (`'kilometres'` instead of `'km'`). Offering only 1 or 2 tools made the local model pick a wrong date tool, because the right one was never shown.

## What an answer costs (agent39)
All four models (flash-lite, flash, pro, local) got all 12 questions right, but Pro wrote 13 times the output tokens of flash-lite (11,346 against 864) and took about 10 times as long, mostly hidden thinking. A router that
sent only the hard questions to Pro still cost 8.6 times flash-lite's output tokens, because the small model alone was already accurate enough. A cap of 60 or 20 output tokens made Gemini's visible reply EMPTY, since thinking
tokens count against the cap. Caching the 5,000-token beginning explicitly served 5,219 of about 5,224 input tokens from the cache; Gemini's automatic caching appeared only on the third call. A first run of parts 2-4
silently used the local model, because the provider was not passed explicitly: when comparing models, name the provider in the code.

## Plan for failure (agent40)
Three layers: retry for short problems (429), a time limit for calls that hang, and a backup model for problems that last. A `FallbackLlm` wrapper (a subclass of ADK's `BaseLlm`) tried Gemini, and when it failed (a wrong model
name gave a 404) or timed out, answered with the local model, and the user still got the right fact. A circuit breaker skipped the dead primary for 30 seconds, so the second model call of the same turn did not wait for another failure.
A tool wrapped in `asyncio.wait_for` returned an error after 3 seconds instead of freezing the chat for 10.

## A secret belongs to the tool, not to the conversation (agent41)
The toolset added `Authorization: Bearer <token>` to each HTTP request, so the model never saw the token (a check before every model call said `False`). Putting the token in the instruction instead made Gemini simply tell
the user, and the local model said "I am not allowed to share it" and printed it in the same sentence. With no credential at all, ADK did not send the request: it asked the app for credentials (`adk_request_credential`),
which `adk run` cannot answer, so the reply was empty.

## A supervisor decides step by step (agent42)
A supervisor that calls a planner, a writer and a fact checker as tools caught a deliberately wrong "500,000 km" for the Moon (the sheet says 384,400 km) on both models and sent the draft back for one rewrite. The number of rewrites varied
between runs (0 to 2), which is the difference from a fixed `LoopAgent`. The checker found errors the writer had made because it had a separate source of truth.

## Streaming changes when, not what (agent43)
With `StreamingMode.SSE` the local model showed its first words after 0.9 s instead of 13 s (217 partial events), while Gemini, whose 4-second reply was already fast, gained a second or two and sent only 5 chunks. Streaming
does not make the model faster or cheaper. Each partial event holds a piece, and the final event repeats the whole text, so print the partials and store the final.

## An agent is a program you can serve (agent44)
`adk api_server` exposed the same agent over HTTP with sessions, `/run` (all events) and `/run_sse` (events as they happen), with no change to `agent.py`. A plain `httpx` client was enough. With
`--session_service_uri sqlite+aiosqlite:///...` a session survived a server restart (4 events kept). The server has no login: it must sit behind your own. The Dockerfile was written but not tested, because no Docker daemon was running.

## A table needs a calculator, not a reader (agent45)
With a 24-row grade table pasted into the prompt and no help, Gemini got 6 of 7 questions right (it gave the overall average as 73.46; the true value is 71.79) and the local model 3 of 7 (a wrong average, wrong best class, wrong count and wrong median). With pandas tools that
do the arithmetic, both models got 7 of 7, and Gemini's built-in code execution also got 7 of 7. A formula tool that only accepts number columns and `+ - * /` never runs the model's text. A bar chart drawn in code was saved as an artifact, and its values matched pandas exactly.

## A workflow can be a graph (agent46)
ADK 2's `Workflow` lists steps (nodes) and arrows (edges). A node is a function or an agent, and a function can return a route name to choose the arrow. In a homework-feedback flow the model only judged the type of reply (correct, arithmetic, concept, off-topic); code routed it to one of four branches, and the off-topic branch was a plain function with no model call.
The routing was right for 12 of 12 replies on Gemini and 11 of 12 on the local model. `@node(retry_config=RetryConfig(...))` re-ran a step that failed ("Node receive failed and is being retried locally"). The feature is new in ADK 2, and joins, parallel workers and node timeouts were not tried.

## Batch jobs need four things (agent47)
Labelling 36 reviews: concurrency 1, 4 and 8 took 36.0, 12.9 and 4.7 seconds on Gemini (7.7 times faster at 8), but only 58.9 and 46.6 seconds at 1 and 4 on the local model, which serves one request at a time. With 30 percent of attempts failing on purpose, 4 attempts with growing waits rescued all 36 items (16 retries); at 80 percent, 15 items gave up and the script listed them.
Writing each result when it is done let a stopped run resume: the second run skipped 15 items and did the remaining 21.

## Permissions belong in code (agent48)
A student tried seven kinds of messages (a plain request, "I am the teacher", a fake system message, "it is only a test", ...) to change or delete data, 28 runs per mode, counting data changes rather than replies. With a careless prompt ("Do what the user asks") the local model gave in 28 of 28 runs and Gemini 8 of 28; with a firmly worded prompt both held (0 of 28); with a check in a `before_tool_callback`, 0 of 28 by construction, since the role comes from session state that only the application writes.
The firm wording made the local model more hesitant about the student's own legitimate request (1 of 4 worked). A per-user rate limit stopped the tool after 5 calls on Gemini, but the local model still repeated the grades from the conversation: a limit protects the backend, not what the model already knows.

## A big model can teach a small one (agent49)
Pro labelled 60 school-office messages using written house rules (59 of 60 right, about 47,000 tokens and 405 seconds, once). Small models then used the 3 most similar labelled examples without the rules: the local model went from 18 to 21 of 24 and flash-lite from 21 to 22. Examples with the true labels gave the same scores, so the teacher's one mistake did not matter here.
But simply giving the rules in words scored best (23 and 24 of 24), and agent37's 36 hand-written examples did as well or better than the 60 teacher-labelled ones: measure the plain prompt before building a teacher pipeline.

---

# Part 4: Check your understanding

Try to answer each question yourself before reading the answer. The agent in brackets is where you can see it happen.

## Basics (agents 01-06)

**1. What turns a language model into an agent?**
An instruction, tools it may choose to call, and a runner that loops until the model gives a final answer. The model decides when to call a tool. (agent02, agent04)

**2. Does the model run your Python function?**
No. It asks for a call by name with arguments. ADK runs the function and sends the result back. The model only sees the function's name, docstring and type hints. (agent04)

**3. Why can't you move `google_search` to a local model?**
It is a built-in Gemini feature, not your code. A local model needs tools that you write yourself. (agent02, agent03)

**4. What is the difference between the conversation history and session state?**
History is the messages of the conversation. State is a small dictionary your tools and agents read and write, such as a list of notes. Both last for one session. (agent05)

**5. A schema forced the reply into valid JSON. Is the content therefore correct?**
No. A schema fixes the shape, not the truth. The phone-case question got a valid but wrong topic. (agent06)

## Multi-agent and workflows (agents 07-10)

**6. Who decides which agent runs next in a coordinator with sub-agents? And in a `SequentialAgent`?**
With sub-agents, the LLM decides by reading their descriptions. In a `SequentialAgent`, your code fixes the order. (agent07, agent08)

**7. When should you use a workflow agent instead of letting the LLM route?**
When the steps are known in advance. LLM routing handled a two-part question with messy hand-offs; a fixed pipeline does the same steps every time. (agent07, agent08)

**8. Why must parallel branches use different `output_key` values?**
They write to the same session state. Two branches with the same key overwrite each other. (agent09)

**9. How do you stop a loop from running forever?**
A stop signal you trust (here, plain code that checks the rules) plus `max_iterations` as a safety cap. (agent10)

**10. Why did the slogan checker become plain Python instead of an LLM?**
The LLM critic miscounted words and later skipped its tool. Rules that code can check should be checked by code. (agent10)

## Safety and control (agents 11, 15)

**11. Name the three callbacks in agent11 and what each one protects.**
`before_model_callback` keeps card numbers away from the model, `before_tool_callback` rejects bad arguments such as 500 pizzas, and `after_model_callback` removes internal contact details from replies. (agent11)

**12. A user writes a card number in words and the guardrail misses it. What does that teach?**
Pattern checks can be dodged. A guardrail is a safety net, not a wall. (agent11)

**13. Why is a confirmation step safer than an instruction that says "ask the user first"?**
ADK enforces the pause around the tool call, so the model cannot skip it. "I am the manager, no need to confirm" did not work. (agent15)

**14. When would you use a guardrail, and when a human approval?**
A guardrail for rules you can decide in advance. A human for actions that are sometimes fine and sometimes not. (agent11, agent15)

## Tools and other agents (agents 12, 14, 27)

**15. What does MCP add compared with a normal function tool?**
The tools live in a separate program, and the agent discovers them at startup. One server can serve many agents. (agent12)

**16. The agent said a book was available when it was not. Where do you look first?**
At the tool. `list_books` did not return availability, so the model filled the gap. (agent12)

**17. What is the difference between transferring to a sub-agent and using an agent as a tool?**
After a transfer the specialist takes over the conversation. With `AgentTool` the caller gets the result back and stays in charge. (agent07, agent14)

**18. Why give a sub-agent an `input_schema`?**
So it takes named arguments (`text`, `target_language`) instead of one vague string. Without it, the local model forgot to pass the language. (agent14)

**19. When would you choose A2A over MCP?**
MCP exposes tools. A2A exposes a whole agent with its own model and instructions, often owned by another team. (agent12, agent27)

**20. Why can a remote agent's answer not be trusted blindly?**
The caller only receives text. A remote local model made up a shipping price, and the caller could not tell. (agent27)

## Retrieval: RAG (agents 16-20)

**21. Why does chunking matter?**
Chunk boundaries decide what can be found. A fixed 300-character cut split a price in half. (agent16)

**22. When does overlap help, and when not?**
It helps only when it is longer than the facts you need to keep whole. A 40-character overlap made things worse. (agent16)

**23. What is an embedding?**
A list of numbers that represents the meaning of a text. Texts with similar meaning get vectors that point in similar directions. (agent17)

**24. Why must questions and documents be embedded with the same model?**
Each model has its own space. A question from one model and a document from another scored 0.03, which is meaningless. (agent17)

**25. What does cosine similarity measure, and why ignore vector length?**
The angle between two vectors. The direction carries the meaning; the length does not. (agent18)

**26. A ranking always returns a top result. Why is that a problem, and what helps?**
For a question the document cannot answer, the top result is still irrelevant. A minimum score helps, plus an instruction to check that the passage really answers the question. (agent18, agent19, agent20)

**27. Can one minimum score separate answerable from unanswerable questions?**
Not here. The coffee question scored higher than several real answers. Choose the cut-off from your own data and model. (agent19)

**28. What is hybrid search?**
Combining meaning (embeddings) with exact word matches. It rescued exact names and codes, but cost one normal question, so measure it. (agent19)

**29. Why does a RAG agent cite the section it used?**
So you can check that the answer really comes from the document, not from the model's own knowledge. (agent20)

## Memory, files and exact answers (agents 21-23)

**30. Name three places an agent can keep information, and how long each lasts.**
Session state (one session), long-term memory (across sessions), and artifacts (versioned files). (agent05, agent21, agent23)

**31. Why didn't "When is my chem test?" find "chemistry exam" in memory?**
`InMemoryMemoryService` matches shared words, not meaning. (agent21)

**32. What should a memory feature always include?**
A way to delete memories, and a rule never to store secrets. Memory is personal data. (agent21)

**33. When does a model need a tool for maths?**
Whenever the exact answer matters. Both models got a long multiplication and a compound-interest question wrong without code. (agent22)

**34. Why must model text never be passed to `eval`?**
It would run any Python code. The calculator parses the expression and allows only numbers and a few operators. (agent22)

**35. What happens when you save an artifact with the same name twice?**
A new version is created and the old one is kept, so you can go back. (agent23)

## Reasoning and quality (agents 13, 24-26)

**36. What two things does an eval check for each case?**
The action (the tool calls and their arguments) and the answer (compared to a reference). (agent13)

**37. Why was the word-overlap metric not enough?**
It passed "is available" against "is not available", because almost every word matched. An LLM judge caught the difference. (agent13)

**38. A conversation eval fails only on turn 2. What does that usually mean?**
The agent lost or misused context from turn 1, for example what "it" refers to. Single-question tests cannot see this. (agent25)

**39. Why keep a strict tool-call check next to an LLM judge?**
The judge scored a non-answer 1.0 every time, while the tool-call check caught the problem. (agent25)

**40. Does more thinking always help?**
No. Easy puzzles were solved without it. On a hard puzzle, Gemini's thinking helped. Measure before you pay for it. (agent24)

**41. Does a planner work the same on every model?**
No. The prompt-based planner was erratic on Gemini but worked every time on the local model. (agent24)

**42. How do you investigate a slow or wrong agent run?**
Look at the sequence of model calls and tool calls, with timing and tokens, before reading the final text. (agent26)

**43. Where did most of the time go in a typical run?**
Waiting for the model (79 to 96 percent), not running tools. (agent26)

## Images, context and safety (agents 28-34)

**44. How does an image reach the model?**
As one more part of the message, next to the text: the image bytes and their type, for example `image/png`. (agent28)

**45. Your code failed to attach an image, but the model described it anyway. What went wrong, and what is the fix?**
The model answered about content it never received. Tell it plainly in the request that the file is missing. (agent28)

**46. Why is a long chat with images expensive?**
Every call sends the whole conversation again, including every earlier image, and one image can be about 1,800 tokens. (agent28, agent30)

**47. What is an instruction provider, and when is it called?**
A function that builds the instruction from session state. ADK calls it before every model call. (agent29)

**48. Why add a worked example (few-shot) to an instruction?**
Models copy examples closely. One example kept the answer format exact, where a description in words did not. (agent29)

**49. The agent says "I've updated your level". How do you check that it really did?**
Look at the state (or the printed instruction), not the reply. A model can claim an action it never performed. (agent29, agent34)

**50. Why does every call get more expensive in a long conversation?**
The model has no memory; the whole history is sent each time. (agent30)

**51. What is the risk of keeping only the last few turns?**
Facts from earlier turns are forgotten, and the model may answer confidently that they were never said. (agent30)

**52. What is the risk of summarising old turns?**
The summary is written by a model and can drop or change facts, and the original turns are no longer sent. (agent30)

**53. What is prompt injection?**
Text inside data the agent reads (a page, a review, an email) that pretends to be an instruction for the AI. (agent31)

**54. Why is a filter of known attack phrases not enough?**
Attackers rephrase. The politely worded lamp note passed the filter. Combine it with an instruction that treats page text as data, output checks, and few
powerful tools. (agent31)

**55. What does `OpenAPIToolset` do?**
It reads a service's OpenAPI description and creates one tool per endpoint; each call becomes a real HTTP request. (agent32)

**56. What happens when a tool's service is down, and how do you handle it?**
The exception stops the run. An `on_tool_error_callback` can turn it into an error result the model can explain. (agent32)

**57. How should an agent handle a job that takes minutes?**
Start it and return a ticket at once, then report progress on request; or use `LongRunningFunctionTool` and send the result back when it is ready. (agent33)

**58. What is the difference between `user:books` and `chat_topic` in state?**
`user:books` belongs to the user and is visible in all their sessions. `chat_topic` has no prefix, so it belongs to one session only. (agent34)

**59. Why store sessions in a database?**
So a conversation can be continued later, from another program run or another server, by its session id. (agent34)

## Search, tools, cost and serving (agents 35-44)

**60. Why use both vector search and keyword search?**
They fail in opposite places. Vectors understand meaning but can blur a form code or a name; keyword search (BM25) finds exact rare words but knows nothing about meaning. (agent35)

**61. What is reciprocal rank fusion, and why not just add the two scores?**
Each chunk earns `1 / (60 + place)` from every ranking, so a chunk high in both lists wins. Cosine scores and BM25 scores have different scales, so adding them needs a weight you must tune; places can be combined without one. (agent35)

**62. What can a reranker do that vector search cannot, and what can it not do?**
It reads the question and a chunk together, so it can tell which candidate really answers. But it only reorders the few candidates it is given: if the right chunk was not found, it cannot rescue it, and it costs a model call per question. (agent35)

**63. Why score retrieval and the answer separately?**
They fail for different reasons and need different fixes. A question whose right chunk was ranked first still got "I couldn't find that" because the chunk was cut in the middle of a sentence: the fix was in chunking, not in search or the prompt. (agent36)

**64. Can an answer be "grounded" and still wrong?**
Yes. An answer can be fully supported by the passage it was given and still miss what the user needed, if the wrong passage was retrieved. Grounded means nothing was made up; correct means the user got the answer. (agent36)

**65. How does choosing few-shot examples with embeddings differ from always showing the same ones?**
The examples most similar to the new message carry the matching rule. In the school-office test it gave 22/24 on the local model against 20 for fixed examples and 18 for none; on Gemini all methods were within two messages. (agent37)

**66. Can examples in a prompt make a model worse?**
Yes. Three random examples gave the local model 16/24, below the 18/24 it scored with no examples. Examples are evidence the model weighs, and unrelated evidence misleads. (agent37)

**67. Why do many tools cost money even when they are not used?**
Every tool's name, description and arguments are sent with every model call. With 20 tools that was about 3,000 prompt tokens on the local model and about 1,000 on Gemini, per call. (agent38)

**68. What do vague tool descriptions break?**
In the test, not the choice of tool (the names were clear) but the arguments: without "units: mm, cm, m, km ..." the models wrote `'kilometres'` and the tool failed 6 to 8 times in 24 questions. (agent38)

**69. How can an ADK agent offer only some of its tools for each message, and what is the risk?**
A toolset's `get_tools` runs before every model call, so it can pick the tools nearest in meaning to the message. If the right tool is not among those offered, the model cannot call it: with only 1 or 2 tools offered the local model chose a wrong date tool. (agent38)

**70. How do retry, timeout and fallback differ?**
Retry handles short problems (429, brief outages); a timeout stops a call that hangs; a fallback switches to a backup model when the primary keeps failing. Retrying a service that is really down only makes the user wait. (agent40)

**71. What is a circuit breaker?**
It remembers that the primary just failed and skips it for a short time, so each following call goes straight to the backup. Without it, every model call in a turn waits for its own failure. (agent40)

**72. Why should every tool have a time limit?**
A tool that never answers freezes the whole conversation. Wrapped in `asyncio.wait_for`, a stuck tool returned an error after 3 seconds, which the model explained honestly. (agent40)

**73. How should an agent get the secret an API requires, and why is "do not reveal it" in the prompt not enough?**
The toolset should add it to the HTTP request, outside the model's context. Written in the instruction, the token was repeated by Gemini on request, and the local model refused and revealed it in the same sentence. (agent41)

**74. What does ADK do when a tool needs a login and no credential is configured?**
It does not send the request. It asks the application for credentials with a special `adk_request_credential` call; `adk run` cannot answer, so the reply is empty. (agent41)

**75. How is a supervisor different from `SequentialAgent`, `LoopAgent` and transfer?**
The model decides the next step and how many rounds to run, and it keeps control of the conversation (the specialists are called as tools). The others are fixed by you, or hand the conversation over. (agent42)

**76. Why does a separate fact checker catch mistakes the writer made?**
It has its own source of truth (a fact sheet it looks up), not the same memory that produced the error. The wrong "500,000 km" was corrected to 384,400 km. (agent42)

**77. What does streaming change?**
How soon the user sees the first words, not the total time, the cost or the quality. On the local model the first text came after 0.9 s instead of 13 s. The partial events hold pieces; the final event repeats the whole text. (agent43)

**78. What does `adk api_server` give you, and what must you add?**
Sessions, `/run` and `/run_sse` as HTTP endpoints, with no change to the agent. It has no login, so put your own authentication in front of it, and use `--session_service_uri` to keep sessions across restarts. (agent44)

**79. Which two ways cut the cost of an agent that sends the same long text every time?**
Context caching (an explicit cache served 5,219 of about 5,224 input tokens from the cache, about 1.5 to 2 seconds per call) and a shorter prompt. Only the unchanged beginning can be cached. (agent39)

**80. Why not trust one measurement on 24 questions?**
Results move with small changes: adding one line of system instruction changed one local row by four messages, and the same lab on two models differed by one or two messages. Treat small differences as noise and look at what is stable across runs and models. (agent37, agent39)

## Data, flows, batches and permissions (agents 45-49)

**81. Why should a model not answer questions about a table by reading it?**
Averages, counts and medians need exact arithmetic over many values. Reading a 24-row table, Gemini got 6 of 7 questions right and the local model 3 of 7, with confident wrong numbers. Let code do the calculation. (agent45)

**82. How can an agent calculate over data safely?**
Give it tools that run pandas for it, and when a tool takes a formula, parse it and allow only numbers, number columns and `+ - * /`. Never pass model text to `eval()`. Gemini's code execution is a sandboxed alternative, but it cannot see your files. (agent45, agent22)

**83. How is a `Workflow` graph different from `SequentialAgent`, `LoopAgent` and transfer?**
You list nodes and edges yourself, and a node can return a route name to choose an edge. Your code decides what runs next, from a verdict the model gives, so the structure is predictable and testable. (agent46)

**84. What can a node be, and why make a branch a plain function?**
A node is a function (no model, instant, always the same) or an agent (one model call). A branch that can be written in code, such as a fixed redirect, costs nothing and cannot go wrong. (agent46)

**85. What does a retry setting on a node do?**
If the step raises an error, ADK waits and runs it again (`RetryConfig`: attempts and delays), so one flaky step does not end the whole run. (agent46)

**86. What does a batch job need that a chat does not?**
Concurrency (a limited number of items at once), retries with growing waits, each result saved as soon as it is done, and resume that skips finished items. And it must list what it could not do. (agent47)

**87. Why is more concurrency not always faster?**
The service sets the ceiling. Gemini was 7.7 times faster at 8 at once; the local model, which serves one request at a time, was only 1.3 times faster at 4. A service's rate limit also caps it. (agent47)

**88. Why use a fresh session for each item in a batch?**
Otherwise each answer sits in the history of the next one: the prompt grows and items can influence each other. A batch worker should be stateless. (agent47)

**89. Why is "students may not delete" in the prompt not a permission system?**
A prompt is a request. With a careless wording the local model obeyed every attack (28 of 28) and Gemini 8 of 28; a firm wording held in 28 runs, but that proves nothing about the next attack or model. A check in a `before_tool_callback` does not read the user's words at all. (agent48)

**90. Where should the user's role come from?**
From your application, through the session state at login. Text typed by the user, such as "I am the teacher", can never change it. (agent48)

**91. What does a rate limit on a tool protect, and what not?**
It protects the backend behind the tool from too many calls. It cannot take back what the model already knows from the conversation: after the block, the local model still repeated the grades from the history. (agent48)

**92. What is distillation by labelling, and when is it worth it?**
A large model labels many examples once; a small model uses them every day. In the school-office test the local model went from 18 to 21 of 24 with teacher-labelled examples. It pays when the task is repeated often and the knowledge is hard to write down. (agent49)

**93. What should you try before building a teacher pipeline?**
A good prompt with the rules written out: it scored 23 and 24 of 24 here, better than the 3 similar teacher-labelled examples (21 and 22). (agent49)

**94. If the teacher makes a mistake, what happens?**
Its mistakes are passed on to the students. In the test one wrong label out of 60 changed nothing, but a teacher wrong on one important kind of message would teach that error to every student, so check a sample of its labels. (agent49)

## Putting it together

**95. How do you stop an agent from making things up when the data is missing?**
Ground it: answer only from tool or retrieved data, return the needed fields from your tools, say "I couldn't find that" when nothing matches, and label any guess as a guess. No method removes made-up answers completely; the aim is to make the line between fact and guess visible. (agent12, agent20, `triage_agent`)

**96. How do you know your agent still works after you change the prompt or the model?**
Run an eval set with both a tool-call check and an answer check on every change, and add a new case for every bug you find. (agent13, agent20, agent25)

**97. What changes when you switch to a small local model?**
It is slower and less reliable at counting, at calling a tool again in later turns, and at strict judgement. Keep each decision small and move checkable rules into code. (agent10, agent20, agent25, agent27)
