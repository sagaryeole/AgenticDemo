# agent21_memory: cases, easiest first

Concept: long-term memory. Session state (agent05) is lost when the conversation ends. Long-term memory survives it:
the agent can recall something you told it last week.
Topic: a study buddy that remembers your exam date and how you like things explained.
Two parts in this folder:
- `agent.py`: the agent, with memory stored in a JSON file. Run: `uv run adk run agent21_memory`
- `memory_service_demo.py`: ADK's own `MemoryService` and `load_memory` tool in a short script.
  Run: `uv run python agent21_memory/memory_service_demo.py`
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT21_MODEL_PROVIDER` for this agent only.

The agent writes to `agent21_memory/memory.json` (ignored by git). To start fresh, delete that file, or run with another file:
`MEMORY_FILE=/tmp/my_memory.json uv run adk run agent21_memory`. Memory is stored per user. `adk run` always uses the user
id `test_user`.

## How it executes
Control: the LLM decides when to save and when to recall (the instruction tells it to recall at the start). The storage is plain code.

```
 CONVERSATION 1 (one adk run)                       memory.json  (a file on disk)
 user: "My chemistry exam is on 14 November,
        and I prefer short explanations."
   LLM ── remember("Chemistry exam is on 14 November") ───► writes ─┐
   LLM ── remember("Prefers short explanations") ──────────► writes ─┤   {"test_user": [
 (the program exits: session state is gone)                          │      {"id":1,"fact":"Chemistry exam ..."},
                                                                     │      {"id":2,"fact":"Prefers short ..."} ]}
 CONVERSATION 2 (a NEW adk run, new session, empty state)            │
 user: "What do you know about me?"                                  │
   LLM ── recall("") ◄───────────────────────── reads ───────────────┘
   LLM: "Your chemistry exam is on 14 November and you prefer short explanations."
```

## Case 1: it saves what matters
> Hi! I'm studying for my chemistry exam on 14 November, and I prefer short explanations.

Expect: a friendly reply, and two facts in `memory.json`: "Chemistry exam is on 14 November" and "Prefers short explanations".
Learn: the model chooses what is worth remembering and writes it as a short, self-contained fact. Open the file and read it.

## Case 2: it remembers in a new process
Quit (`exit`), start `uv run adk run agent21_memory` again, and ask:
> What do you know about me?

Expect: both facts, even though this is a new session with empty state. Then ask "Explain what a mole is." and the answer is short.
Learn: the memory came from the file, not from the conversation. Compare agent05, where a new session started empty.

## Case 3: forgetting
> Please forget my exam date.

Expect: the agent looks up the fact and deletes it. Ask "What do you know about me?" and only the explanation style is left.
Check `memory.json`.
Learn: a memory feature needs a way to delete. Users should be able to correct or remove what an agent stored about them.

## Case 4: small talk is not saved
> Thanks! It's a rainy day today, isn't it?

Expect: a friendly reply, and no new entry in `memory.json`.
Learn: the instruction says to save only lasting facts. Without such a rule, memories fill up with noise. It is guidance, not a
guarantee: a model may occasionally save something you would not.

## Case 5: memory is read, not assumed
Delete `memory.json`, start the agent, and ask "What is my exam date?"
Expect: it says it does not know, with no made-up date.
Learn: "Never claim to remember something that recall did not return" is the grounding rule from agent05, applied to memory.

## Case 6: look at what is stored (privacy)
Open `memory.json`.
Expect: plain text, readable by anyone with access to the machine, keyed by user id.
Learn: memory is personal data. A real system needs consent, access control, and deletion. Never store secrets (passwords,
card numbers) in memory. This is also why the file is in `.gitignore`.

## Case 7: ADK's own memory service (the demo script)
Run `uv run python agent21_memory/memory_service_demo.py`.
Expect: in session A you state the facts. The script then calls `memory.add_session_to_memory(session)`. In session B, a brand-new
session, the agent calls `load_memory(...)` and answers "14 November" and "organic reactions". In session C it says it does
not know your favourite football team.
Learn: this is ADK's built-in pattern: a `MemoryService` stores finished sessions, and the `load_memory` tool searches them.
Memory does not save itself: the script has to call `add_session_to_memory`. In session A of a local run the model even called
`load_memory` unprompted and found nothing yet.

## Case 8: keyword search versus meaning
    uv run python agent21_memory/memory_service_demo.py "When is my chem test?"

Expect: on both Gemini and the local model the agent does not find the exam. It calls `load_memory('chem test')` and answers that
it does not know.
Learn: `InMemoryMemoryService` matches shared words, and "chem test" shares none with "chemistry exam". Production memory
services search by meaning (embeddings, as in lab 17-19). This one is for learning and testing, and it forgets everything
when the program ends.

## Case 9: which memory to use
| | Session state (agent05) | File memory (agent21 `agent.py`) | ADK MemoryService (demo script) |
|---|---|---|---|
| Lives for | one session | until you delete the file | one program run (in-memory version) |
| Written by | tools | tools | your code, from finished sessions |
| Found by | key | keyword in the fact | keyword (in-memory) or meaning (production services) |
| Good for | this conversation | a simple, persistent, inspectable memory | the standard ADK pattern, and cloud services in production |

Learn: start with session state. Add long-term memory only for facts that must survive across conversations, and decide who can
see and delete them.
