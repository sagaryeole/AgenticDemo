# agent36_rag_eval: cases, easiest first

Concept: how do you know a RAG system is good? A wrong answer can come from two different places, and each needs a different fix:
- RETRIEVAL: the search did not bring back the chunk that holds the answer (fix: chunking, embeddings, hybrid search, k).
- ANSWER: the chunk was there, but the model answered wrongly or made something up (fix: instruction, model).
A single "was the final answer right?" check cannot tell them apart. This lab scores every question at each step.
Topic: the Riverside library handbook again (agent20). 12 questions the handbook answers, 3 it does not.
Run: `uv run python agent36_rag_eval/rag_eval.py` (add `--show` to print every answer, `--k 5` to give the model more chunks).
Local: `MODEL_PROVIDER=local EMBEDDING_PROVIDER=local uv run python agent36_rag_eval/rag_eval.py` (about 1 minute; Gemini about 3).
It is a lab, like agents 16-19: it does what agent20 does, but without ADK, so the same pipeline can be run for 15 questions and 3 chunking
strategies in one go.

| score | how it is decided |
|---|---|
| retrieved | the chunk containing the answer phrase is among the top 3. `MRR` (mean reciprocal rank) adds the rank: 1 for rank 1, 0.5 for rank 2, 0.33 for rank 3, 0 if missing |
| correct | the answer contains the key fact (a plain text check, for example "25 cents") |
| grounded | a second model call says YES if every fact in the answer is stated in the passages |
| refused | for an unanswerable question, the answer is "I couldn't find that in the handbook." |

## How it executes
```
 for each of 3 chunking strategies:                    for each of the 15 questions:
   chunk the handbook ─► embed ─► index                   ┌─ question ─► search top-3 chunks ──────► RETRIEVAL score  (is the answer chunk there? rank?)
                                                          │                    │
                                                          │                    ▼  chunks + question
                                                          │            model answers from the chunks only
                                                          │                    │
                                                          └────────────────────┼──► ANSWER scores   (correct? grounded? refused when it should?)
                                                                               ▼
                                              one table row per strategy: where does it lose points?
```

## Case 1: run it
Expect (from testing, same numbers each time on the local model):

| chunking | chunks | right chunk in top 3 | MRR | correct | grounded | refused |
|---|---|---|---|---|---|---|
| fixed+overlap | 14 | 11/12 | 0.83 (local) / 0.76 (Gemini) | 10/12 (local) / 11/12 (Gemini) | 10/12 (local) / 11/12 (Gemini) | 3/3 |
| paragraphs+heading | 18 | 11/12 | 0.92 | 11/12 | 12/12 (local) / 11/12 (Gemini) | 3/3 |
| sections | 10 | 12/12 | 0.96 (local) / 1.00 (Gemini) | 12/12 | 12/12 | 3/3 |

Learn: with whole sections as chunks, everything was found and answered on both models. The numbers give you something to compare, in place of
"it seems to work". The table is also a regression test: change the chunk size or the embedding model, run it again, see which column moved.

## Case 2: a retrieval failure
Run with `--show` and find "How do I join the library?" under `paragraphs+heading` (and `fixed+overlap`).
Expect: `retrieved at rank None`, so the right chunk (the one with "photo ID") was not in the top 3. Gemini answered "I couldn't find that in the
handbook." The local model answered from a different chunk about the application form for children.
Learn: when retrieval fails, the answer step can only do its best with the wrong text. Gemini's refusal is the safe outcome. The local model's
answer sounds reasonable, is partly true, and does not tell the user what they asked for: "To join, bring a photo ID" is missing.

## Case 3: an answer failure, with the right chunk in hand
Run the local model with `--show` and find "Which form do I need to register for the Coding Club?" under `fixed+overlap`.
Expect: `retrieved at rank 1` (the chunk with form LB-204 was found first), but the answer was "I couldn't find that in the handbook."
Learn: this is the second kind of failure, and the retrieval score alone would have missed it. Printing the chunk shows why: the rank-1 chunk begins
in the middle of a sentence, `'s 10 to 14 meets on Thursdays at 16:00 and needs registration through form LB-204.` The words "Coding Club" were cut
off, and the chunk that does contain them ends at "needs registratio". The model could not tell which club the form was for, and it refused to guess.
Retrieval was fine; the fix is in the chunking (lab 16: `sections` or overlap), not in the search or the instruction.

## Case 4: "grounded" is not the same as "correct"
Look at the local `paragraphs+heading` row: grounded 12/12 but correct 11/12.
Learn: the answer about joining the library was fully supported by the passage it was given, so the judge said YES. It was just not the
passage the user needed. Grounding measures whether the model made things up. Correctness measures whether the user got the answer. You need both.
(The judge is itself a model and can be wrong, so read some answers before trusting a score.)

## Case 5: unanswerable questions
Expect: 3 of 3 refused in every row, on both models. Learn: the instruction "use ONLY the passages, otherwise say you couldn't find it" held for these
three. Do not read much into it: three questions is a small test, and agent20's case 3 showed a weak chunk can make a model less sure. Add more
tricky unanswerable questions (ones that are close to the handbook's topics) to see it fail.

## Case 6: change one thing, measure again
Run `--k 1`, then `--k 5`.
Expect: not measured here. With k = 1 the right chunk must be first (MRR matters), and with k = 5 it is easier to find but the model reads more text.
Learn: that is what the table is for. Change one setting at a time and see which columns move.

## Case 7: honest limits
Learn: 12 + 3 questions are enough to see the shape of the problem, not to prove that one setting is better by a small margin: one question is worth 8 points.
A real evaluation set has dozens or hundreds of questions, written by people who did not build the system. The questions here were written by the same
author as the handbook, which makes them easier than real users' questions (agent35 used rephrased questions for that reason).
