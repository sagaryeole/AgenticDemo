# agent14_agent_as_tool: cases, easiest first

Run: `uv run adk run agent14_agent_as_tool`.
Concept: `AgentTool` lets one agent call another agent like a function. The caller keeps control of the conversation.
Topic: a greeting-card writer that calls a translator agent when you ask for another language.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT14_MODEL_PROVIDER` for this agent only.
The agent prints a `[tool call] ...` line each time it calls the translator.

## How it executes
Control: the LLM decides whether to call the translator (like any tool). The card writer stays in charge
and writes the final answer.

```
 user: "Birthday message for Anna in Swedish"
        │
        ▼
 ┌─────────────┐  1. writes English message
 │ card_writer │
 │   (LLM)     │  2. tool call: translator(text, target_language="Swedish")
 └──┬───────▲──┘                    │
    │       │ 4. result comes       ▼
    │       │    back like any   ┌────────────┐
    │       └────────────────────┤ translator │  3. its own model call,
    │                            │   (LLM)    │     returns only the translation
    │                            └────────────┘
    ▼ 5. card_writer writes the final answer (English + Swedish + a note)
  reply

 Compare agent07 (transfer):
   root_agent ──transfer──► weather_agent ... the specialist now owns the conversation and the next turns
   card_writer ──call──► translator ........ the translator returns a result and the card writer carries on
```

## Case 1: the tool is called
> Write a birthday message for my friend Anna in Swedish.

Expect: a `[tool call] translator({'text': ..., 'target_language': 'Swedish'})` line, then a reply with the English
message, the Swedish translation and a short note. The reply is written by `[card_writer]`.
Learn: another agent can be a tool. The translator ran its own model call, but the user only sees the card writer.

## Case 2: no tool needed
> Write a thank-you note for my teacher.

Expect: an English message and no `[tool call]` line.
Learn: as with any tool, the model decides. The instruction says to translate only when a language is named.

## Case 3: the caller keeps control
In the same session:
> Now write a get-well message for my neighbour in French.

Expect: a second tool call with `target_language` French, and the reply is again from `[card_writer]`.
Learn: unlike agent07, no other agent took over the conversation. The caller delegates one job and continues.

## Case 4: a typed input matters
Look at `TranslationRequest` in `agent.py`. During development this agent first had no `input_schema`.
Then an agent-as-tool takes a single free-text `request`. The local model called
`translator({'request': 'Happy Birthday, Anna! ...'})` without any language, so the translator had nothing to translate
into and just returned English. Gemini happened to write "target_language: Swedish" inside the string.
Learn: a sub-agent's `input_schema` turns one vague string into named arguments (`text`, `target_language`), like a
function signature. Try it: delete `input_schema=TranslationRequest` and compare the `[tool call]` line.
Put it back afterwards.

## Case 5: the model skipping the tool
Ask for several translations in new sessions, on the local model.
Expect: usually a tool call. Small models sometimes answer without calling the tool, or translate on their own
even though the instruction says never to.
Learn: the instruction guides, but does not force. If you must guarantee a translation, call the translator from code.

## Case 6: transfer or tool?
| | Transfer (agent07, `sub_agents`) | Agent as a tool (agent14, `AgentTool`) |
|---|---|---|
| Who talks to the user next | the specialist | the original agent |
| Result goes | straight to the user | back to the caller first |
| Good for | handing the whole conversation over | getting one piece of work done, then combining it |
| Cost | one agent per turn | caller + callee model calls on every use |

Learn: use a tool when the caller must combine, check, or reformat the result. Use a transfer when the specialist
should take the conversation.
