# agent07_multiagent: cases, easiest first

Run: `uv run adk run agent07_multiagent`, or `uv run adk web` to see the hand-offs.
Concepts: sub-agents with narrow jobs, and the global model switch (`common/models.py`).
Topic: a travel helper with a weather specialist and a currency specialist.

## How it executes
Control: THE LLM DECIDES. The coordinator chooses a specialist from their descriptions, and
the path is different for different questions.

```
 user message
      │
      ▼
 ┌────────────┐  general question   ┌───────────────────┐
 │ root_agent ├────────────────────►│ answers itself    │
 │ (LLM picks)│                     └───────────────────┘
 └──┬───────┬─┘
    │       │ money question
    │       └──────────────► currency_agent ──► convert_currency() ──► answer
    │ weather question
    └──────────────────────► weather_agent  ──► get_weather() ───────► answer

 After a transfer, the specialist keeps the next turns until control moves again.
```

## Part A: the model switch (the global feature)

Agents from 07 onwards get their model from `common/models.get_model()`, not from hardcoded values.
Choose the provider for all of them with an environment variable:

    MODEL_PROVIDER=local  uv run adk run agent07_multiagent    # LM Studio
    MODEL_PROVIDER=gemini uv run adk run agent07_multiagent    # Gemini

You can also put `MODEL_PROVIDER=local` in the project root `.env` (the factory loads it).
Override a single agent: `AGENT07_MODEL_PROVIDER=gemini` beats `MODEL_PROVIDER`.
Other settings: `LOCAL_MODEL_ID`, `LOCAL_API_BASE`, `GEMINI_MODEL`.
Gemini needs the GOOGLE_* variables in `agent07_multiagent/.env`; local needs LM Studio running.

Run case 1 under both providers and compare the answer style and speed.

## Case 1: transfer to one specialist
> What is the weather in Tokyo?

Expect: root_agent transfers to weather_agent, which reports sunny, 26°C.
Learn: the coordinator picks a specialist by reading the `description` fields.

## Case 2: a different specialist
> How much is 100 USD in EUR?

Expect: transfer to currency_agent, answer 90 EUR.
Learn: each specialist owns one narrow job and one tool.

## Case 3: no specialist needed
In a new session:
> What is a passport?

Expect: root_agent answers itself, with no transfer.
Learn: transfer is a choice, driven by the coordinator's instruction.

## Case 4: the specialist keeps the conversation
In one session, ask the weather question, then the currency question, then:
> What is a passport?

Expect: the answer comes from currency_agent (the last specialist), not root_agent.
Learn: after a transfer, the specialist stays in charge of later turns until
something transfers control again. Watch the agent name in `adk web`.

## Case 5: a tool that fails
> What is the weather in Atlantis?

Expect: weather_agent reports "No weather data for Atlantis" and does not invent a forecast.
Learn: a tool's error message is passed through to the answer, so return clear errors.

## Case 6: two requests in one message
> What is the weather in Paris, and how much is 50 USD in SEK?

Expect: results vary by model. On `qwen3.5-9b` weather_agent answered first, then
currency_agent answered the rest and repeated the weather. Another model may answer
only one part.
Learn: a transfer hands the turn to one agent at a time, so multi-part requests are
handled by chained hand-offs, which is not guaranteed to be tidy or complete. A more
controlled way to combine specialists is a good topic for the next agent.
