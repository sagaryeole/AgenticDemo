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

# Part 3: What agents 14-27 showed

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

## Putting it together

**44. How do you stop an agent from making things up when the data is missing?**
Ground it: answer only from tool or retrieved data, return the needed fields from your tools, say "I couldn't find that" when nothing matches, and label any guess as a guess. No method removes made-up answers completely; the aim is to make the line between fact and guess visible. (agent12, agent20, `triage_agent`)

**45. How do you know your agent still works after you change the prompt or the model?**
Run an eval set with both a tool-call check and an answer check on every change, and add a new case for every bug you find. (agent13, agent20, agent25)

**46. What changes when you switch to a small local model?**
It is slower and less reliable at counting, at calling a tool again in later turns, and at strict judgement. Keep each decision small and move checkable rules into code. (agent10, agent20, agent25, agent27)
