# agent19_retrieval: cases, easiest first

This step is a **lab, not an agent**: a script that measures retrieval on a small question set. There is no `adk run`.
Run (fast, about 2 seconds): `EMBEDDING_PROVIDER=local uv run python agent19_retrieval/retrieval_lab.py`
Run with Gemini embeddings (about 4-5 minutes, because of API latency): `uv run python agent19_retrieval/retrieval_lab.py`
Concept: retrieval logic. Cosine similarity (lab 18) ranks chunks. Retrieval logic decides how many to return (top-k),
when to return nothing (a minimum score), and how to combine meaning with exact words (hybrid search).
The code is the `Index` class in `common/rag.py`: labs 16-18 put together.

The test: 12 questions the handbook can answer, each with a phrase the right chunk must contain; 3 questions it cannot
answer ("Where can I park my bicycle?", "What is the capital of France?", "Does the library sell coffee?"); and 5 short
exact-term queries ("LB-310", "Riverside-Guest", ...).
All numbers below come from running the lab on both providers. 12 questions is a small sample: one question changes a
result by 8 points, so treat the tables as illustrations, not proof.

## How it works
```
 question ──embed──► q                                        ┌───────────────────────────────┐
                      │                                       │ Index = chunks + their vectors│
                      ▼                                       └───────────────┬───────────────┘
        cosine(q, every chunk)  ──────────────────────────────────────────────┘
                      │
                      ▼  add an exact-word bonus      score = cosine + weight × (words found exactly in the chunk)
                      │
                      ▼  sort, best first
        ┌─────────────────────────────┐
        │ keep the first k            │   top-k
        │ drop any below min_score    │   threshold  ──► maybe an EMPTY list = "nothing relevant found"
        └──────────────┬──────────────┘
                       ▼
                chunks for the model
```

## Case 1: top-k (Part 1)
Expect (small chunks, `fixed+overlap`): the answer is among the top 1 chunk for 9 of 12 questions. Among the top 2 it is
11 of 12 (local) or 10 of 12 (Gemini), and top 3 or 5 gives 11 of 12 on both.
Learn: a bigger k catches more answers, but it also hands the model more text, some of it irrelevant. One question
("How do I join the library?") is never found at any k with small chunks, because the paragraph with the answer never ranks
high enough.

## Case 2: chunking decides the result (Part 2)
Expect (identical on both providers): best chunk correct for 9/12 (`fixed+overlap`), 11/12 (`paragraphs`), 12/12 (`sections`),
11/12 (`paragraphs+heading`). Top 3: 11, 11, 12, 11.
Learn: lab 16 showed all strategies except `fixed` keep every fact whole, but whole facts are not enough. A chunk also
has to look like the question. A whole section ("Membership") matches "How do I join?" better than one paragraph of it.
Also notice that adding the heading to each paragraph did not help on this set (11/12 either way), so test your own idea
instead of assuming it works.

## Case 3: a minimum score (Part 3)
Expect (local embeddings): the best score for the 12 answerable questions runs from 0.48 to 0.78, and for the 3
unanswerable ones from 0.38 to 0.55. Gemini: 0.51-0.77 against 0.45-0.62.
Local table:

| minimum score | answerable kept | unanswerable rejected |
|---|---|---|
| 0.50 | 11/12 | 2/3 |
| 0.60 | 7/12 | 3/3 |
| 0.70 | 4/12 | 3/3 |

Gemini: at 0.50 it keeps 12/12 and rejects 1/3; at 0.65 it keeps 6/12 and rejects 3/3.
Learn: the two ranges overlap, so no threshold is perfect. A higher cut-off rejects more bad questions but also loses good
ones. "Does the library sell coffee?" scores 0.62 on Gemini, higher than several correct matches. Choose the threshold from
your own data, and recheck it when you switch models (lab 17, case 5).

## Case 4: a question with no answer
Try one unanswerable question yourself, first with a minimum score of 0.65, then with none:

    EMBEDDING_PROVIDER=local uv run python -c "from common.rag import Index, sections, load_handbook; \
    idx = Index(sections(load_handbook())); \
    print(idx.search('Where can I park my bicycle?', k=3, min_score=0.65)); \
    print(len(idx.search('Where can I park my bicycle?', k=3)))"

Expect: `[]` (an empty list), then `3`. All three unanswerable questions gave an empty list at 0.65 on both providers. At 0.6,
Gemini still returned one chunk for the coffee question (its best score is 0.617).
Learn: returning nothing is a valid result. The price of 0.65 is that it also rejects about half of the good answers (case 3
table). So agent20 uses a lower cut-off and tells the model to check that the passage really answers the question, and to say
"I couldn't find that in the handbook" when it does not.

## Case 5: exact words rescue short queries (Part 4)
Expect (`paragraphs+heading` index): with weight 0.0, 4 of the 5 exact-term queries find their chunk. With weight 0.2 all 5 do.
Which query is rescued depends on the embedding model: with the local model it is `Riverside-Guest` (the Wi-Fi network
name), with Gemini it is `What is form LB-204 for?`. In each case the embeddings alone ranked another chunk first.
Learn: embeddings capture meaning, so a bare name or code can get lost among similar-sounding chunks. Exact word matching
catches it. Combining the two is called hybrid search.

## Case 6: the boost has a cost (Part 4)
Expect: the 12 normal questions go from 11/12 to 10/12 when the weight rises. Local: at 0.5. Gemini: already at 0.2.
Learn: exact words also lift chunks that just repeat common words from the question. A small weight helped in this lab, but
not for free. Compare both columns before you keep a boost, and try values between the ones shown.

## Case 7: change a rule and re-measure
Edit `part3_threshold` thresholds, or `part4_keyword_boost` weights, or the `ANSWERABLE` list. Add a question of your own
with the phrase its answer contains, and see which chunking strategy handles it.
Learn: this is how retrieval is tuned in practice: a list of questions with known answers, and numbers that go up or down
when you change a setting. It is also the idea behind evals (agent13), applied to search.

## Case 8: the settings to carry into agent20
Chunking: `sections` (best here). k: 3 (the model gets a little extra context). Minimum score: just below the lowest score
of a good answer in your data. Keyword weight: 0, unless exact names or codes matter, then a small value, measured.
Learn: there is no universal setting. These came from this handbook, this question set and these two embedding models.
