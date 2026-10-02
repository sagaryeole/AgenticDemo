# agent35_hybrid_rerank: cases, easiest first

Concept: one search method is rarely best at everything. Meaning search (embeddings, labs 17-19) understands "sandwich" and "food", but can
blur a form code. Keyword search (BM25) nails exact words but knows nothing about meaning. Hybrid search uses both, and a reranker
then re-reads the best few candidates with a language model.
Topic: the same Riverside Community Library handbook as labs 16-20, chunked as `paragraphs+heading` (18 chunks).
Run: `uv run python agent35_hybrid_rerank/rerank_lab.py`. With `MODEL_PROVIDER=local EMBEDDING_PROVIDER=local` in front it takes under a minute
(the embedding model `text-embedding-embeddinggemma-300m` must be loaded in LM Studio). With Gemini it takes about 3 minutes.
The code is in `common/rag.py` (`BM25`, `reciprocal_rank_fusion`, `llm_rerank`).
It is a lab, like agents 16-19: no agent to chat with, because the point is to measure the search step on its own.

## How it executes
```
 question: "What happens if I return a novel after the due date?"
        │
        ├──► 1. vectors   embed the question, cosine against every chunk ──► ranking A   (understands meaning)
        │
        ├──► 2. BM25      count the question's exact words in every chunk ──► ranking B   (understands words, no model)
        │
        ▼
   3. hybrid: reciprocal rank fusion      score(chunk) = 1/(60 + place in A) + 1/(60 + place in B)
        │                                 a chunk that is high in BOTH lists wins; scores are never mixed, only places
        ▼  top 5 candidates
   4. rerank: ONE model call reads the question and all 5 chunks together, scores each 0-10
        │
        ▼
   final order, best first
```

## Case 1: meaning search on its own
Run the lab and read PART 1 (questions in different words from the handbook, such as "quiet booths" for study rooms).
Expect (from testing, 8 questions): the vectors row finds the right chunk first 5 times (both models), and in the top 3 almost always (8 of 8 with
Gemini, 7 of 8 local).
Learn: embeddings match meaning, so a "sandwich" question finds the chunk about food. They still get about a third of these wrong at
position 1, which is why the later steps exist.

## Case 2: keyword search is the opposite
Read the BM25 row in PART 1, then PART 2 (exact terms: `LB-310`, `555-0142`, `Riverside-Guest`, `Helen Park`).
Expect: BM25 is weak on the paraphrased questions (3 of 8 first) because the question shares few words with the answer. On the exact terms it
is perfect (6 of 6) while vectors miss one (5 of 6).
Learn: each method fails where the other is strong. A code, a name or a phone number has no "meaning" for an embedding, but BM25 finds it
because it is a rare word, and rare words count most.

## Case 3: hybrid search
Read the hybrid row. Expect (from testing): on the paraphrased set 6 of 8 first on both models (one better than vectors, which had 5);
on exact terms 6 of 6 (local) or 5 of 6 (Gemini, no better than vectors there).
Learn: reciprocal rank fusion merges two rankings using only their places, never their scores. Cosine (0 to 1) and BM25 (any size) cannot be
added directly, so using places avoids choosing weights. Compare agent19's keyword boost, which needed a weight you had to tune.
Hybrid is a safe middle: it is never far from the better of the two methods, but on its own it did not fix everything either (Gemini's exact-term
row shows hybrid at 5 of 6, because the weaker ranking pulled the right chunk down).

## Case 4: the reranker
Read the last row. Expect (from testing): paraphrased 8 of 8 first (Gemini) and 7 of 8 (local); exact terms 6 of 6 on both.
Learn: the earlier steps look at the question and a chunk SEPARATELY (the chunk's vector is made before any question exists). A reranker
reads them TOGETHER, so it can tell that "return a novel after the due date" is answered by "Late books cost 25 cents per day" and not by the
chunk about lost items. Part 3 of the lab picks the question where the methods disagree most: the right chunk was at position 2 (vectors),
7 (BM25), 2 or 3 (hybrid) and 1 after reranking.

## Case 5: what reranking costs
Read the last line of the lab: `the rerank step made 14 model calls`, and compare the time: about 45 seconds locally and about 190 seconds
with Gemini for 14 questions (a share of that is the embeddings).
Learn: a rerank is one extra language-model call for EVERY question, which adds a second or more and costs tokens. So it only reads the few
candidates a cheap search already picked. The usual design is a funnel: cheap and wide first (vectors + BM25 over thousands of chunks), then
expensive and narrow (rerank 5 to 20).

## Case 6: the reranker can only reorder
Change `llm_rerank(question, [... top5 ...])` in `orderings` so it gets only the top 2, and look at questions where the right chunk was 3rd.
Expect (by construction, not measured): the reranker cannot rescue a chunk that was never given to it.
Learn: reranking improves the ORDER of candidates. If the right chunk is not among them, the earlier steps (chunking, embeddings, hybrid)
must find it. Measure recall of the candidate list (case 4's "in top 3" column) before tuning the reranker.

## Case 7: be honest about the sample
Learn: 8 and 6 questions are enough to see the pattern and not enough to claim a precise gain. One question changes a row by 12 or 17 points,
and the two models differ by a question or two. Use the numbers as a direction, and build a larger set (agent36) for decisions.
