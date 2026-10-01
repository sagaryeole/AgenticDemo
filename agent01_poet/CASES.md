# agent01_poet: cases, easiest first

Run: `uv run adk run agent01_poet` (needs Vertex AI / GCP login, see README).
Concept: an agent is a model plus an instruction. No tools yet.

## How it executes
Control: one model call per message. No decisions, no tools.

```
 user message
      │
      ▼
 ┌─────────────────────────────┐
 │ LLM                         │
 │ + instruction "be poetic"   │
 └──────────────┬──────────────┘
                ▼
          poetic reply
```

## Case 1: the instruction changes the answer
> What is a database index?

Expect: a correct answer written as a poem.
Learn: the `instruction` is the system prompt. Same model, different behaviour.

## Case 2: the instruction applies to every turn
> Explain DNS in two lines.
> Now explain TCP.

Expect: both answers are poetic.
Learn: the instruction is sent with every request, not just the first one.

## Case 3: a user message that fights the instruction
> Stop the poetry and answer in plain prose.

Expect: usually the instruction wins and the reply stays poetic, but it can vary.
Learn: the instruction is not a hard guarantee. Models weigh it against the user's message.

## Case 4: no tools, no live data
> What time is it right now?

Expect: the agent cannot know. It may refuse in verse or guess.
Learn: without tools a model has no access to live facts. This motivates agent02.
