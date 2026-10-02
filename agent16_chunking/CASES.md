# agent16_chunking: cases, easiest first

This step is a **lab, not an agent**. It is plain Python with no model and no network, so there is no `adk run`.
Run: `uv run python agent16_chunking/chunking.py`
Concept: chunking. Before a program can search a long document, it cuts the document into pieces ("chunks"). Where
you cut decides what can be found later.
Document: `data/handbook.md`, the Riverside Community Library Handbook (about 3,400 characters, used in steps 16-20).
Measure: the lab checks 11 key facts (for example "Late books cost 25 cents per day, up to a maximum of 5 dollars per
book"). A fact is "intact" if one chunk contains all of it. A fact cut across two chunks cannot be answered from one chunk.

## How it works
```
  handbook.md  (one long text)
        │
        ▼
 ┌────────────────────┐        fixed_size(300):  cut every 300 characters, wherever that falls
 │  chunking strategy │   or   sentences(2):     keep sentences whole, 2 at a time
 └─────────┬──────────┘        sections():       one chunk per "## heading" section
           ▼                   ...
   chunk 0 │ chunk 1 │ chunk 2 │ ...        ◄── "Printing costs 10 cents per black-and-" | "white page and 50 cents..."
           ▼                                        a bad cut splits one fact into two useless halves
   count how many of the 11 facts survive whole
```

## Case 1: compare six strategies
Run with no options.

Expect (deterministic, from testing):

| strategy | chunks | facts intact |
|---|---|---|
| fixed (300 chars) | 12 | 9 / 11 |
| fixed+overlap (300, overlap 60) | 14 | 11 / 11 |
| sentences (2 per chunk) | 24 | 11 / 11 |
| paragraphs | 18 | 11 / 11 |
| sections | 10 | 11 / 11 |
| paragraphs+heading | 18 | 11 / 11 |

Learn: cutting by a fixed number of characters ignores the meaning of the text, so it can split a fact in half.

## Case 2: see the damage
Read the "Example of a fact cut in two" lines at the bottom of the output.
Expect: the printing price is cut in the middle: one chunk ends `...black-and-` and the next starts `white page and 50 cents...`.
Learn: neither half answers "How much does colour printing cost?" on its own. Search would find a chunk that sounds
right but does not contain the answer.

## Case 3: overlap helps, but only if it is big enough
Run `--size 200 --overlap 40`, then `--size 300 --overlap 60`.
Expect: with size 200 and overlap 40, `fixed+overlap` keeps only 6 of 11 facts (worse than plain `fixed`, 10 of 11).
With size 300 and overlap 60 it keeps all 11.
Learn: overlap repeats the end of one chunk at the start of the next, so a cut fact shows up whole in at least one
chunk. That works only if the overlap is longer than the fact. These facts are 50-100 characters, so an overlap of 40
is not enough. More overlap also means more chunks to store and search.

## Case 4: let the document's structure decide
Compare `sentences`, `paragraphs` and `sections` in the table. Print one: `--show sections`.
Expect: all three keep every fact whole, because the author's own boundaries (sentence ends, blank lines, headings)
are natural places to cut.
Learn: if your text has structure, use it. Character counts are the fallback for text that has none.

## Case 5: chunk size is a trade-off
Run `--show sections` and look at the sizes (136 to 438 characters).
Expect: a section chunk holds several related sentences, so one chunk can answer several questions. But a bigger chunk
mixes more topics, which makes its meaning blurrier when it is turned into numbers in step 17.
Learn: small chunks are precise but can lose context. Large chunks keep context but are less precise. There is no
universal best size. Step 19 measures it on real questions.

## Case 6: a chunk should say what it is about
Run `--show paragraphs`, then `--show paragraphs+heading`.
Expect: the second version puts the section title in front, for example `Opening hours: On public holidays the library
is closed...`. The first version has the same sentence with no title.
Learn: when you cut a document into paragraphs, each piece loses the heading above it. Adding the title back costs
a few characters and tells the search what each chunk is about. Step 19 shows whether it helps.

## Case 7: break it yourself
Change the sentence list `FACTS` at the top of `chunking.py` (use sentences from `data/handbook.md`), or try
`--size 100`, `--size 1000`.
Expect (from testing, with `--overlap 20`): at size 100, `fixed` keeps 8 of 11 facts and `fixed+overlap` only 3 of 11,
because the overlap is far shorter than a fact. At size 1000 every fact survives, but there are only 4 chunks of about
840 characters.
Learn: the measure ("are the facts whole?") is only one side. A huge chunk keeps every fact but is hard to search.
