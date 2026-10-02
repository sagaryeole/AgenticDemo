# agent17_embeddings: cases, easiest first

This step is a **lab, not an agent**: a Python script that calls an embedding model. There is no `adk run`.
Run: `uv run python agent17_embeddings/embeddings_lab.py`
Local model: `EMBEDDING_PROVIDER=local uv run python agent17_embeddings/embeddings_lab.py`
Concept: an embedding model turns text into a vector (a list of numbers) so a program can compare meaning, not just
spelling. Two texts with similar meaning get vectors that point in similar directions.
Setup: Gemini (default) needs the `GOOGLE_*` settings in `.env`. Local needs LM Studio running with an embedding model
loaded (`text-embedding-embeddinggemma-300m` by default, set `LOCAL_EMBEDDING_MODEL` to change it).
The code that calls the models is in `common/embeddings.py`.

## How it works
```
   "The library is closed on Sunday."
                  │
                  ▼
        ┌──────────────────┐
        │ embedding model  │   (a different model from the chat model: it only produces numbers)
        └────────┬─────────┘
                 ▼
   [-0.008, -0.033, -0.010, -0.026, ... 768 numbers ...]      ◄── one vector per text, length 1.0

   texts                    vectors (matrix)
   ┌─────────────┐          ┌───────────────────────────┐
   │ chunk 0     │   ───►   │ 0.01 -0.03  0.02 ... 768  │  row 0
   │ chunk 1     │          │ 0.04  0.00 -0.01 ... 768  │  row 1
   │ ...         │          │ ...                       │
   └─────────────┘          └───────────────────────────┘
```

## Case 1: what a vector looks like (Part 1)
Expect: shape `(1, 768)`: one text, 768 numbers. The first few numbers are small and mean nothing on their own.
The length (norm) of the vector is `1.000`.
Learn: the numbers are only useful in comparison. These models return vectors scaled to length 1, which makes
comparing them simple (lab 18).

## Case 2: meaning, not spelling (Part 2)
Expect: a 3x3 similarity matrix. "I deposited my paycheck at the bank" is closer to "She opened a savings account"
than to "We had a picnic on the river bank". Gemini: 0.792 versus 0.745. Local: 0.608 versus 0.575.
Learn: the word "bank" appears in two sentences, but the embedding tells them apart by context. The margin is
modest, not dramatic. Do not read a score as a probability, and do not expect a clean gap.

## Case 3: a question and its answer (Part 3)
Expect: for "How much does it cost when I return a book late?" the sentence "Late books cost 25 cents per day..."
ranks first (Gemini 0.739, local 0.788), ahead of printing prices and study rooms.
Learn: the question has almost no words in common with the answer. A keyword search for "cost" and "return" would
miss it. This is why embeddings are used for search.

## Case 4: the whole document as a matrix (Part 4)
Expect: 10 sections give a matrix of shape `(10, 768)`.
Learn: that matrix is a complete "vector index". Searching later means comparing the question's vector with each row.
Real systems store millions of rows in a vector database, but the idea is the same.

## Case 5: scores are not comparable across models
Compare the two providers' numbers in cases 2 and 3 (run the script twice, once with `EMBEDDING_PROVIDER=local`).
Expect: the same ranking, but different absolute numbers (0.79 vs 0.61 for the same pair in Part 2).
Learn: a score of 0.7 means different things in different models. A threshold ("only accept above 0.7", lab 19) must
be chosen for the model you use, and rechecked if you switch.

## Case 6: question or document? (Part 5, Gemini only)
Expect: the same question scores 0.739 against the right answer when embedded as a `query`, and 0.919 when embedded as
a `document`. The unrelated sentence goes from 0.454 to 0.765, so the gap shrinks from 0.285 to 0.154.
Learn: Gemini embedding models take a task setting. Use `query` for the question and `document` for the text you
search. With the wrong setting the ranking can still be right here, but it is less clear-cut, and a threshold set for one
setting will not work for the other.

## Case 7: never mix models (Part 6)
Expect: both models return 768 numbers, so the math runs without an error. Gemini question vs Gemini answer: 0.739.
Local vs local: 0.788. Gemini question vs local answer: 0.027, which is meaningless.
Learn: each model has its own "space". Embed the documents and the questions with the same model, and if you switch
models, embed everything again. A mix-up gives plausible-looking numbers and no error message, which makes it a quiet bug.

## Case 8: try your own sentences
Edit the lists in Parts 2 and 3. Try two sentences that mean the same thing with different words, then two that share
words but mean different things.
Learn: embeddings capture a lot, but they are not perfect. Exact codes and names ("form LB-204") are a known weak spot.
Lab 19 shows how to handle that.
