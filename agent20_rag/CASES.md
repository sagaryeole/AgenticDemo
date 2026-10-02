# agent20_rag: cases, easiest first

Run: `uv run adk run agent20_rag`, or `uv run adk web`.
Concept: RAG (retrieval-augmented generation). The agent searches a document first, then answers only from what it found.
It puts together labs 16-19: chunking (`sections`), embeddings, cosine ranking, and retrieval rules (top-3, minimum score).
Topic: a Q&A agent for the Riverside Community Library handbook (`data/handbook.md`).
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT20_MODEL_PROVIDER` for this agent only.
Embeddings follow the chat provider unless you set `EMBEDDING_PROVIDER`. So `MODEL_PROVIDER=local` is fully local: chat and
search both run in LM Studio (the embedding model `text-embedding-embeddinggemma-300m` must be loaded).
The agent prints a `[search_handbook] 'query' -> [(section, score), ...]` line for every search, so you can see what it found.
The first question is slower, because the handbook is embedded on first use.

## How it executes
Control: the LLM decides to search (the instruction tells it to do so for every question). The retrieval itself is plain code.

```
 user: "Can I eat in the study room?"
        │
        ▼
      LLM ── tool call: search_handbook("eat in the study room")     ◄── the model rewrites the question as a search query
                │
                ▼
   ┌───────────────────────────────────────────────────────────────┐
   │ embed the query ─► cosine against every section vector        │   labs 17-18
   │ keep the top 3, drop any below the minimum score              │   lab 19
   └─────────────────────────┬─────────────────────────────────────┘
                             ▼
      passages: [("Study rooms", 0.61, "...Food is not allowed...")]   or   []  = nothing relevant
                             │
                             ▼
      LLM writes the answer using ONLY those passages, and cites the section:
      "No, food is not allowed in the study rooms, but water in a closed bottle is fine. [Study rooms]"
      (if the passages do not contain the answer: "I couldn't find that in the handbook.")
```

## Case 1: an answer from the handbook
> How much is the late fee for a book?

Expect: a `[search_handbook]` line with "Late fees and lost items" first (about 0.75), then "Late books cost 25 cents per day, up to
a maximum of 5 dollars per book. [Late fees and lost items]".
Learn: the answer comes from the retrieved passage, not from the model's memory, and it names its source.

## Case 2: the model rewrites your question
> Can I eat in the study room?

Expect: the search line shows a shorter query such as `'eat in the study room'`, and the reply cites [Study rooms].
Learn: the model turns the question into the search text. It may drop or change words, so retrieval depends on the model too.

## Case 3: a question the handbook cannot answer
> Where can I park my bicycle?

Expect: "I couldn't find that in the handbook." In testing the search sometimes returned nothing (below the minimum score), and
sometimes a weak chunk (score about 0.45, for "Computers and printing"). In both cases the model still said it could not find it.
Learn: two safety nets work together. The minimum score drops clearly irrelevant chunks (lab 19), and the instruction makes the
model check that the passage really answers the question. Neither is perfect alone: a threshold cannot catch everything.

## Case 4: a question outside the handbook entirely
> What is the capital of France?

Expect: "I couldn't find that in the handbook." Often there is no search line at all, because the model sees that the question is
not about the library.
Learn: the instruction forbids answering from its own knowledge, so a correct but ungrounded answer ("Paris") is not allowed.
This agent's job is to be the handbook's voice, not a general assistant.

## Case 5: a question that needs more than one passage
> My 10-year-old wants to join the Coding Club. What do we need to do?

Expect: a reply that mentions form LB-204, and possibly the parent signature rule from the Membership section. Answers vary between
runs: in testing one reply cited only "Events and children's programs", another added the guardian rule from "Membership".
Learn: with top-3, several passages can reach the model, and what it combines is up to the model. It is a good place to
check that each statement is really in the passages.

## Case 6: follow-up questions still search
Ask several questions in one session, including an unanswerable one in the middle, then an answerable one.
Expect: a new `[search_handbook]` line for each question.
Learn: during development the local model searched on the first question, then stopped searching and copied its earlier
"I couldn't find that" reply to every later question, answerable ones included. Adding "For EVERY new question, call
search_handbook first ... Never reuse a previous answer without searching again" fixed it. Models imitate their own earlier
replies, so a long session needs this kind of reminder.

## Case 7: weaken the instruction and see what changes
Replace the whole `instruction` in `agent.py` with: `"You are a helpful assistant for the Riverside Community Library. You can use the
search_handbook tool if it helps."` Ask "What is the capital of France?", "Who is the director?" and "Where can I park my bicycle?".
Expect (from testing): with the local model, "The capital of France is Paris." and, for the director, a reply saying it has no
information, without searching, although the handbook names the director. Gemini still declined France and answered the director.
Learn: the retrieval code did not change, but the agent now answers from its own knowledge, and sometimes skips the search. The
instruction is half of the system. Restore the original afterwards.

## Case 8: run the eval
    uv run adk eval agent20_rag agent20_rag/rag.evalset.json --config_file_path agent20_rag/rag_config.json

Expect: 5 passed, 0 failed on both Gemini and the local model. Five cases: three answerable, two unanswerable.
Learn: this reuses the idea from agent13: write the questions and expected answers down once, and rerun on every change.
The check uses an LLM judge on the final answer. It does not match tool arguments exactly, because the model rewrites queries
(case 2), so exact matching would fail for good answers.

## Case 9: what the eval does and does not catch
With the generic instruction from case 7, run the eval on Gemini.
Expect: 4 passed, 1 failed. `outside_knowledge` fails, because Gemini now says "I can only answer questions about the Riverside
Community Library Handbook. I cannot tell you the capital of France." instead of "I couldn't find that in the handbook."
Learn: that failure is a change of wording, not a wrong answer. The eval flagged a change in behaviour, and a person still has to
decide if it matters. With the local model in case 7 the change was a real hallucination ("Paris"). Read the failing case before
deciding what it means.

## Case 10: tune retrieval with lab 19
Change `TOP_K` or `MIN_SCORE` in `agent.py`, or switch the chunking to `paragraphs_with_heading` in `common/rag.py`.
Run cases 1-5 and the eval again.
Learn: retrieval settings and the instruction are separate dials. Tune retrieval with the lab 19 numbers and the instruction
with the eval.
