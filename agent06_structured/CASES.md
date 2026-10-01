# agent06_structured: cases, easiest first

Run: `uv run adk run agent06_structured` (LM Studio server must be running).
Every reply should be a JSON object matching `AlertTriage`, with no prose around it.

## How it executes
Control: one model call whose reply must match a schema. No tools for this agent.

```
 free-text alert
      │
      ▼
 ┌─────────────────────────────┐   schema (AlertTriage) is sent with the request
 │ LLM, forced to reply in JSON│◄──────────────────────────────────────────────
 └──────────────┬──────────────┘
                ▼
 {"service": ..., "severity": ..., "category": ..., ...}
                │
                └──► also saved to state["triage"] (output_key)
```

## Case 1: clear alert, all fields present
> payments-api returning 500 for all checkout requests, DB timeout after 30s

Expect: service=payments-api, severity high or critical, category=database,
needs_human=true.
Learn: the reply is JSON that matches the schema, not free text.

## Case 2: low-severity alert
> orders-api: log rotation job took 3 minutes longer than usual

Expect: severity=low, needs_human=false.
Learn: the field descriptions in the schema guide the model, like tool docstrings do.

## Case 3: missing information
> Something is slow, users are complaining

Expect: service="unknown", not an invented service name.
Learn: the instruction decides what happens when the input lacks data.

## Case 4: closed set of values
> auth-service: TLS certificate expires in 2 days

Expect: category is one of the allowed values (probably "security" or "other").
Learn: `Literal` limits the model to a fixed list. It cannot return "tls" or "cert".

## Case 5: state via output_key
Run `uv run adk web`, send an alert, open the session's State tab.
Expect: the JSON appears under `triage`.
Learn: `output_key` saves the result to session state, so the next agent can read it.
This is how agents hand structured data to each other (multi-agent, a later step).
