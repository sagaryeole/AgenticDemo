# agent39_cost_speed: cases, easiest first

Concept: what does an answer COST? Language models are billed in tokens (pieces of words): input tokens (everything you send) and output tokens (everything the model writes, including
Gemini's hidden "thinking"). A bigger model costs more per token, and thinks more, so it is slower. This lab measures tokens and seconds, then tries four ways to spend less.
No prices are printed, because they change: look up the current price list and multiply the token counts by it.
Topic: 12 questions (6 easy ones that need one fact, 6 "hard" ones that need several steps, with exact answers) for the model-size parts; the library handbook for the caching part.
Run: `uv run python agent39_cost_speed/cost_lab.py` (about 10 minutes: the large model thinks a lot), or one part: `--part 1`, `--part 2`, `--part 3`, `--part 4`. Add `--with-local` to include the local model in part 1.
Parts 2-4 always use Gemini (model sizes and caching are Gemini features). It is a lab, like agents 16-19; the code uses `common/llm.py`, which asks a model one question directly.

## How it executes
```
 PART 1  same 12 questions ──► flash-lite │ flash │ pro │ (local)  ──► accuracy, tokens in/out, seconds
 PART 2  question ──► flash-lite: "EASY or HARD?" (1 token) ──┬─ EASY ──► flash-lite answers
                                                             └─ HARD ──► pro answers
 PART 3  question ──► model with max_output_tokens = 60 / 20       (a hard stop on the length of the reply)
 PART 4  [long text, 5,000 tokens] + question 1 ┐
         [long text, 5,000 tokens] + question 2 ├─► the repeated start is billed at a lower rate if it is CACHED
         [long text, 5,000 tokens] + question 3 ┘      automatic: sometimes     explicit: you create the cache, and every call says "use it"
```

## Case 1: model size
Run part 1. Expect (from testing, 12 questions):

| model | right (easy / hard) | input tokens | output tokens | seconds |
|---|---|---|---|---|
| `gemini-2.5-flash-lite` | 6/6, 6/6 | 511 | 864 | 11 |
| `gemini-2.5-flash` | 6/6, 6/6 | 511 | 3,964 | 26 |
| `gemini-2.5-pro` | 6/6, 6/6 | 511 | 11,346 | 108 |
| local `qwen3.5-9b` | 6/6, 6/6 | 704 | 695 | 48 |

Learn: all four models got every question right, so on THESE questions the larger models bought nothing except cost: Pro wrote 13 times as many output tokens as flash-lite and took 10 times as long, mostly hidden
thinking. (The local model counts tokens its own way, and is free per token but slower than flash-lite on this machine.) The "hard" questions were not hard enough to separate the models: an honest test set must contain
questions that the small model gets wrong, otherwise you cannot tell what the big one is worth. Try harder questions of your own.

## Case 2: a router
Run part 2. Expect (from testing):

| strategy | right | input tokens | output tokens | seconds | calls to the large model |
|---|---|---|---|---|---|
| everything to the small model | 12/12 | 511 | 861 | 14 | 0 |
| everything to the large model | 12/12 | 511 | 9,737 | 91 | 12 |
| routed (small model labels EASY/HARD first) | 12/12 | 1,190 | 7,412 | 76 | 6 |

Learn: the router sent exactly the 6 hard questions to the large model, which cut the output tokens by a quarter and the time a little compared with "always large". But the small model alone was as accurate
and far cheaper, so here the router saved less than simply not using the large model. A router pays off only when the small model really fails on the hard questions; it also adds a call per question (the input tokens
more than doubled). Measure the small model on your own questions first.

## Case 3: capping the output
Run part 3. Expect (from testing, flash): without a cap 1,546 output tokens in 9.4 s. With `max_output_tokens=60` or `20`: output tokens 57 and 17, but the visible reply was EMPTY. Asking "Answer in at most 20 words" gave a
whole sentence ("The atmosphere scatters blue light from the sun more than other colors, making the sky appear blue.") but still 195 output tokens, mostly thinking.
Learn: on Gemini 2.5 the thinking tokens count against the cap, so a small cap can be used up before the model writes a single visible word. Capping is a safety limit (against a runaway answer), not a way to get short answers:
ask for a short answer in the instruction, and set the cap generously. The same limit on a model without thinking would instead cut the answer off in the middle of a sentence. (A first version of this lab accidentally ran part 3 on the
local model, which gave different numbers: always pass the provider explicitly when comparing models.)

## Case 4: caching a long text
Run part 4. The same 5,000-token text is sent with three different questions. Expect (from testing):
- a) Automatic: input tokens about 5,230 each time; served from the cache: 0, 0, then 5,092 on the third call. Time about 1.8 s each.
- b) Explicit (`client.caches.create(...)`, then `cached_content=...` on each call): 5,219 of about 5,224 input tokens served from the cache on every call, 1.5 to 2.0 s.
Learn: cached input tokens are billed at a lower rate. Gemini sometimes caches a repeated start by itself, which you cannot count on (here it appeared on the third call only); an explicit cache is a promise: you create it, say how
long it lives (`ttl`), pay a little for storage, and delete it when done (the lab does). It only works for an unchanging BEGINNING, so put fixed text (instructions, documents) first and the changing question last.
It needs a minimum size (the text here was 5,000 tokens); a short instruction cannot be cached.

## Case 5: tokens in an agent
Print `event.usage_metadata.prompt_token_count` for each model call, as agent28's `ask_with_image.py` and agent38's `tool_choice_test.py` do.
Learn: an agent makes several model calls per question (a tool call, then the answer), and every call resends the instruction, the tool descriptions and the history (agent30). The cost of an agent is calls times tokens per call:
agent38 cut the tool part of that by 70 percent, agent30 the history part.

## Case 6: what to take away
| to spend less | does it work | what it risks |
|---|---|---|
| a smaller model | yes, if it is accurate enough on YOUR questions (case 1) | wrong answers on hard cases |
| a router | only if the small model fails on hard questions (case 2) | one more call, and a wrong EASY label |
| a cap on the output | a safety limit, not a style tool (case 3) | an empty or cut-off answer |
| caching the repeated start | yes, for long unchanged text (case 4) | storage cost, minimum size, order of the prompt |
| fewer tokens in the prompt (agents 30, 38) | yes | losing information |

Learn: measure first. Here the cheapest model was already enough, and the "obvious" tricks (a router, a cap) did less than expected.
