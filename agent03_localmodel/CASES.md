# agent03_localmodel: cases, easiest first

Run: `uv run adk run agent03_localmodel`.
Setup: LM Studio open, model loaded, local server started (Developer tab).
Concept: the same agent running on a local model through LiteLLM. No GCP needed.

## How it executes
Control: same as agent01 (one model call per message). Only where the model runs has changed.

```
 user message
      │
      ▼
 ADK agent ──► LiteLLM ──HTTP──► LM Studio (127.0.0.1:1234/v1)
                                       │
                                       ▼
                              local model (qwen3.5-9b)
                                       │
 reply  ◄──────────────────────────────┘
```

## Case 1: it connects
> Say hello in five words.

Expect: a short reply. In the log you see `provider = openai` and your model name.
Learn: `openai/<id>` plus `api_base` points LiteLLM at LM Studio.

## Case 2: server not running
Stop the LM Studio server and send any message.
Expect: a connection error, not a model answer.
Learn: the agent depends on the local server being up. Errors here are network errors.

## Case 3: wrong model id
Change the id in `agent.py` to `openai/does-not-exist` and send a message.
Expect: an error naming the model, or LM Studio using whatever is loaded.
Learn: the id after `openai/` must match LM Studio. Check `curl http://127.0.0.1:1234/v1/models`.
Change it back afterwards.

## Case 4: quality and speed differ from Gemini
> Explain what a connection pool is in three sentences.

Expect: a reasonable but sometimes weaker or slower answer than a hosted model.
Learn: local models trade quality and speed for cost and privacy.

## Case 5: no tools here
> What time is it right now?

Expect: the model cannot know and may guess.
Learn: switching the model did not add abilities. This motivates agent04.
