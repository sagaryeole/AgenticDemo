# agent06_structured: cases, easiest first

Run: `uv run adk run agent06_structured` (LM Studio server must be running).
Concept: structured output. The reply must be JSON that matches a schema (`ReviewAnalysis`), so other code can use it.
Topic: turning a free-text customer review into a record with `product`, `sentiment`, `topic`, `summary`, `needs_reply`.
Every reply should be a JSON object, with no prose around it.

## How it executes
Control: one model call whose reply must match a schema. This agent has no tools. ADK does allow
tools with `output_schema`: they run first, and only the final answer is forced into the schema.

```
 free-text review
      │
      ▼
 ┌─────────────────────────────┐   schema (ReviewAnalysis) is sent with the request
 │ LLM, forced to reply in JSON│◄──────────────────────────────────────────────────
 └──────────────┬──────────────┘
                ▼
 {"product": ..., "sentiment": ..., "topic": ..., "summary": ..., "needs_reply": ...}
                │
                └──► also saved to state["review"] (output_key)
```

## Case 1: a clear, unhappy review
> My new headphones arrived two weeks late and the box was crushed. Very disappointed.

Expect: product=headphones, sentiment=negative, topic=delivery, needs_reply=true.
Learn: the reply is JSON that matches the schema, not free text.

## Case 2: a clear, happy review
> Love this coffee maker, it makes great coffee every morning.

Expect: sentiment=positive, needs_reply=false.
Learn: the field descriptions in the schema guide the model, like tool docstrings do.

## Case 3: missing information
> It's okay I guess.

Expect: product="unknown", not an invented product name.
Learn: the instruction decides what happens when the input lacks data.

## Case 4: closed set of values
> The blender works great but it is way too expensive for what it is.

Expect: sentiment is one of the allowed words (likely "mixed"), and topic is one of the five allowed topics.
The model cannot return "pricey" or "expensive" as a topic.
Learn: `Literal` limits the model to a fixed list. It also forces a choice: this review talks about both
quality and price, but `topic` takes only one value (the local model chose "quality").

## Case 5: valid shape, wrong content
> Does this phone case fit the older model too?

Expect: valid JSON and `needs_reply=true` (a question). But in testing the local model also set `topic` to
"quality", when "other" fits better, because no allowed topic really matches.
Learn: a schema guarantees the shape of the answer, not that it is correct. When no allowed value fits, the
model picks the closest one. A cheap fix is to give every `Literal` an honest "other" and say when to use it.

## Case 6: state via output_key
Run `uv run adk web`, send a review, open the session's State tab.
Expect: the JSON appears under `review`.
Learn: `output_key` saves the result to session state, so the next agent can read it.
This is how agents hand data to each other (agent08 onwards).
