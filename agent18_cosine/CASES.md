# agent18_cosine: cases, easiest first

This step is a **lab, not an agent**. Parts 1-2 are plain maths with no model. Parts 3-5 use the embedding model from lab 17.
Run: `uv run python agent18_cosine/cosine_lab.py`
Local model: `EMBEDDING_PROVIDER=local uv run python agent18_cosine/cosine_lab.py`
Concept: cosine similarity. It is the number that says how close a question's vector is to each chunk's vector, so a
program can rank the chunks. 1 means they point the same way, 0 means unrelated, -1 means opposite.

## How it works
```
 question ──embed──► q = [0.02, -0.01, ...]
 chunk 0  ──embed──► v0 = [...]      cosine(q, v0) = 0.43
 chunk 1  ──embed──► v1 = [...]      cosine(q, v1) = 0.72   ◄── highest: the best match
 chunk 2  ──embed──► v2 = [...]      cosine(q, v2) = 0.51

 cosine(a, b) =  dot(a, b)  ÷  ( length(a) × length(b) )

            b                 Only the ANGLE between the arrows matters, not their length.
           ╱                  small angle  → cosine near 1 → similar meaning
          ╱  ╲ angle θ        right angle  → cosine 0      → unrelated
         ╱    ╲
        ●──────────► a
```

## Case 1: direction matters, length does not (Part 1)
Expect: a table of five toy vectors compared with `[1, 0]`. The vector `[5, 0]` has dot product 5.00 and distance 4.00,
but its cosine is still 1.00 and its angle 0°. The right-angle vector has cosine 0.00 and the opposite one -1.00.
Learn: for text, direction carries the meaning, and length is mostly noise. Cosine looks only at direction, which makes it
a fair comparison between a short question and a long chunk.

## Case 2: the formula, step by step (Part 2)
Expect: `dot(a, b) = 26.0`, the two lengths 5.0990 and 5.3852, and `cosine by hand` and `cosine in numpy` both printing
0.946864.
Learn: there is no magic. It is multiply, add, divide, and numpy does the same thing faster.
Try it: change `a` and `b` in `part2_by_hand_vs_numpy`.

## Case 3: rank real chunks (Part 3)
Expect (Gemini embeddings, from testing): "How much is the late fee?" ranks "Late fees and lost items" first (0.717, next is
0.569). "Can I bring my lunch into a study room?" ranks "Study rooms" first (0.689, next is 0.522). With local embeddings the
winners are the same (0.704 and 0.673).
Learn: ranking all chunks is one matrix product: `section_vectors @ q`. The best chunk is the one with the highest score.

## Case 4: a question the document cannot answer (Part 3)
Expect: "Where can I park my bicycle?" is not in the handbook, yet a section still ranks first: "Computers and printing" with
0.547 (Gemini) or 0.453 (local). It is lower than the real matches (0.69-0.72 and 0.67-0.70), but nothing in a ranking
says "no answer".
Learn: ranking always returns something. If you hand the top chunk to a model as "the answer", it may build a confident but
wrong reply out of an irrelevant paragraph. The fix is a minimum score, covered in lab 19.

## Case 5: dot product equals cosine (Part 4)
Expect: both vectors have length 1.0000, and the dot product and cosine print the same number, 0.856525 against 0.856524 for
Gemini (a rounding difference).
Learn: since these models return length-1 vectors, you can skip the division and just use the dot product. That is
why one line, `vectors @ q`, scores every chunk.

## Case 6: other distance measures agree (Part 5)
Expect: ranking by straight-line distance gives exactly the same order as ranking by cosine (`same full order? True`).
Learn: for length-1 vectors, "closest by distance" and "highest cosine" are the same thing. Libraries use whichever is
cheaper, so you may see either word in documentation.

## Case 7: scores are only meaningful within one model
Compare Case 3 and 4 across `EMBEDDING_PROVIDER=gemini` and `local`.
Expect: similar rankings, different numbers (a good match is about 0.70 in both, a poor one is about 0.55 in Gemini and 0.45
locally).
Learn: pick any cut-off by looking at scores from the model you use, as lab 19 does.

## Case 8: write your own
Add a function `top_k(question, k)` that returns the titles of the `k` best sections, using `section_vectors @ q` and
`np.argsort`. Test it on the three questions.
Learn: this ten-line function is the core of every simple RAG system. Lab 19 adds the rules around it.
