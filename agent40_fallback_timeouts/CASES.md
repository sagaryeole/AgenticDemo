# agent40_fallback_timeouts: cases, easiest first

Concept: things fail. A model service goes down, a model name is wrong, a call hangs, a tool never answers. A tutorial agent can ignore this; a real
one cannot. Three tools for it: a time limit (a timeout), a second model to switch to (a fallback), and short pauses before trying again (retries).
agent07 onwards already retry rate-limit errors (`common/models.py`); this agent adds the other two.
Topic: a city-facts helper with one tool, `get_city_fact` (Stockholm, Lisbon or Kyoto).
Run: `uv run adk run agent40_fallback_timeouts`. The primary model is Gemini and the backup is the local model (`PRIMARY_PROVIDER=local` swaps them).
Break things on purpose with environment variables in front of the command:
- `BREAK_PRIMARY=down`: the primary model is pointed at something that does not exist (a made-up Gemini model name, or a local port nothing listens on)
- `BREAK_PRIMARY=slow`: the time limit becomes 0.3 seconds, which no real model can meet
- `SLOW_TOOL=1`: the tool sleeps for 10 seconds, as if its service were stuck (the tool's own limit is 3 seconds)
The agent prints `[fallback] ...` when it switches models and `[tool timeout] ...` when a tool is cut off.

## How it executes
```
 user: "Tell me a fun fact about Kyoto."
        │
        ▼
 root_agent  ──►  FallbackLlm  (a model made of two models, defined in agent.py)
                      │
                      ├─ 1. primary model, inside a time limit ── answers ───────────────────────────► reply
                      │            │
                      │            └─ fails (404, no connection ...) or is too slow
                      │                    │  remember: "skip the primary for 30 seconds" (the circuit breaker)
                      │                    ▼
                      └─ 2. backup model ──────────────────────────────────────────────────────────► reply (a different model wrote it)

 tools:  get_city_fact ─ wrapped in  asyncio.wait_for(..., 3 seconds)
            ├─ answers in time ───────► {"fact": ...}
            └─ takes too long ────────► {"error": "did not answer within 3 seconds ..."}  ─► the model tells the user, the chat does not freeze
```

## Case 1: everything works
> Tell me a fun fact about Kyoto.

Expect: "Kyoto has about 1,600 temples." and no `[fallback]` line, in about 3 seconds (tested with Gemini as primary).
Learn: with no failures the extra layer is invisible. The wrapper costs nothing when the primary answers.

## Case 2: the primary model is down
    BREAK_PRIMARY=down uv run adk run agent40_fallback_timeouts
> Tell me a fun fact about Kyoto.

Expect (from testing): `[fallback] primary gemini-no-such-model failed (ClientError: 404 NOT_FOUND ...); using backup openai/qwen3.5-9b`, then the correct fact,
about 14 seconds in total (the local model is slower). With `PRIMARY_PROVIDER=local BREAK_PRIMARY=down` the roles swap: the local call fails
(`InternalServerError`, connection refused) and Gemini answers, about 5 seconds.
Learn: the user got a correct answer although the first-choice model was unreachable. The error is printed, so you can see what happened.

## Case 3: the circuit breaker
Look at the lines printed in case 2. One user message makes TWO model calls: one that asks for the tool, and one that writes the final sentence.
Expect (from testing): the first call prints `primary ... failed (...)`, the second prints `primary skipped (it failed less than 30s ago)`.
Learn: once the primary has failed, trying it again straight away wastes time on every call. A circuit breaker remembers the failure and skips
the primary for a while (`cooldown_seconds`, 30 here). After the pause, the primary is tried again, so it is used again once it has recovered.

## Case 4: the primary is too slow
    BREAK_PRIMARY=slow uv run adk run agent40_fallback_timeouts
Expect (from testing): `[fallback] primary gemini-2.5-flash failed (timed out after 0.3s); using backup openai/qwen3.5-9b`, and the correct fact.
Learn: a model that is slow, not down, is just as bad for a user. A time limit turns "wait forever" into "give up and use the backup". Choose
the real limit from your own measurements: too short and good answers are thrown away, too long and users wait. (0.3 seconds is a test setting.)

## Case 5: a tool that hangs
    SLOW_TOOL=1 uv run adk run agent40_fallback_timeouts
> Tell me a fun fact about Kyoto.

Expect (from testing): `[tool timeout] get_city_fact took longer than 3.0s`, and a reply like "I am sorry, but the tool to retrieve fun facts is currently unavailable."
in about 6 seconds, not 10 or more.
Learn: `with_timeout` in `agent.py` wraps the tool. Without it, a stuck tool freezes the whole conversation. With it, the tool returns an error
that the model reads and explains honestly. (Compare agent32's error callback, which handled a tool that raised an error. This handles one that never returns.)

## Case 6: what a fallback cannot do
Learn: the backup is a DIFFERENT model, so answers can differ in wording, length and quality. The wrapper also collects the primary's whole answer
before showing it, so it does not stream (agent43). If the two models behave differently with tools or instructions, test the backup on its own
(agent38 and agent14 showed that small local models need clearer instructions). A fallback is a safety net, not a replacement for a reliable primary.

## Case 7: retry, timeout, fallback
| | What it handles | Where |
|---|---|---|
| Retry | a short problem: too many requests (429), a brief outage (503) | `retry_options` in `common/models.py`; the primary here keeps 2 attempts |
| Timeout | a call that hangs or is very slow | `timeout_seconds` for models, `with_timeout` for tools |
| Fallback | a problem that lasts: wrong model name, service down | `FallbackLlm` |

Learn: they work in layers. Retry first for the cheap, short problems; give each call a time limit; switch to the backup when it is still failing.
Retrying a service that is really down only makes the user wait.
