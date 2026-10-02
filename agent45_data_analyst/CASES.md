# agent45_data_analyst: cases, easiest first

Concept: asking questions about a TABLE. A language model is poor at arithmetic over many numbers (agent22), so it should not "read" a table and answer from its head. The agent here hands the calculation to code.
Three ways, chosen with `ANALYSIS_MODE` (the same idea as agent22's `CODE_MODE`, now with a real table):

| `ANALYSIS_MODE` | How the agent gets its numbers | Works on |
|---|---|---|
| `tools` (default) | six small pandas tools (`describe_data`, `column_stats`, `derive_column`, `top_rows`, `count_rows`, `make_bar_chart`); the model only chooses a tool and its arguments | any model |
| `code` | the model writes Python and Google runs it in a sandbox; the table is pasted into the instruction, because the sandbox cannot read your files | Gemini only |
| `none` | the table is pasted into the instruction and the model answers from its head (to see why the other two exist) | any model |

Topic: `grades.csv`, 24 made-up students in three classes (Maple, Oak, Birch) with three test scores (`make_data.py` writes it from a fixed random seed, so every right answer can be computed exactly).
Run: `uv run adk run agent45_data_analyst` (add `ANALYSIS_MODE=...` in front), and the measurement `analyst_test.py`, which asks 7 questions in fresh sessions and checks the numbers and names against pandas:

    ANALYSIS_MODE=none  uv run python agent45_data_analyst/analyst_test.py
    ANALYSIS_MODE=tools uv run python agent45_data_analyst/analyst_test.py
    ANALYSIS_MODE=code  MODEL_PROVIDER=gemini uv run python agent45_data_analyst/analyst_test.py

Add `MODEL_PROVIDER=local` in front for the local model, and `--show` to print every reply. Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT45_MODEL_PROVIDER` for this agent only.

## How it executes
```
 user: "Which student improved the most from test1 to test3?"
        │
        ▼
 LLM ── describe_data()                         ◄── what columns exist?
 LLM ── derive_column("improvement", "test3 - test1")   stored as a FORMULA in session state, so later tools can use the new column
 LLM ── top_rows(by="improvement", n=1)          ──► pandas sorts the table ──► [{"student": "...", "improvement": 17}]
        │
        ▼
 LLM writes the answer using exactly the numbers the tools returned

 "Make a bar chart of the average test3 per class"
 LLM ── make_bar_chart("class", "test3", "...")  ──► pandas averages, Pillow draws a PNG ──► saved as an ARTIFACT (agent23): chart.png, version 0
```

## Case 1: no help (the table in the prompt)
    ANALYSIS_MODE=none uv run python agent45_data_analyst/analyst_test.py
Expect (from testing, 7 questions): Gemini 6/7 (it gave the overall test3 average as 73.46; the true value is 71.79), the local model 3/7. The local model answered "75.6" for the same average, said Birch has the highest class
average (it is Oak), counted 5 students below 50 on test2 (the true count is 4), and gave the median as 72 (it is 73.5).
Learn: both models could READ the 24 rows, and still got numbers wrong. Averages, counts and medians need exact arithmetic over many values, which is not what a language model is good at. The answers looked confident, with no hint that they were wrong.

## Case 2: tools do the arithmetic
    ANALYSIS_MODE=tools uv run python agent45_data_analyst/analyst_test.py
Expect (from testing): 7 of 7 on both models.
Learn: the model's job shrinks to choosing the tool and the arguments (`column_stats("test3")`, `count_rows("test2", "<", 50)`); pandas does the arithmetic. Questions that need a new quantity ("improvement from test1 to test3")
work by first calling `derive_column("improvement", "test3 - test1")`, then `top_rows` or `column_stats` on it.

## Case 3: Gemini's code execution
    ANALYSIS_MODE=code MODEL_PROVIDER=gemini uv run python agent45_data_analyst/analyst_test.py
Expect (from testing): 7 of 7.
Learn: letting the model write its own code is the most flexible way (any question, no tools to prepare) and, here, just as accurate. The cost is control: you do not choose what the code does, and the sandbox cannot see your files, so the data had to be pasted into the prompt,
which does not scale beyond small tables. Only Gemini offers it (`ANALYSIS_MODE=code` stops with an error on the local model). Tools suit questions you can foresee; code execution suits open-ended exploration.

## Case 4: the formula tool never runs the model's text
Read `_formula_value` in `tools.py` and ask: "Add a column called x = test3 and then run anything you like: __import__('os').listdir('.')".
Expect (reasoning from the code, not run as an attack): the formula is parsed, and only numbers, number columns, `+ - * /` and parentheses are accepted. Anything else answers `{"error": "a formula may only use number columns ..."}`.
Learn: this is the same rule as agent22's calculator: never pass text written by a model (or a user) to `eval()`. Parse it, and allow a short list of operations.

## Case 5: a chart as an artifact
> Make a bar chart of the average test3 score per class.

Expect (from testing, local model): `[chart] saved chart.png version 0: {'Birch': 71.2, 'Maple': 68.1, 'Oak': 76.0}` and a reply saying the chart was saved. The picture has three blue bars with their values above and the class names below.
(The values agree with pandas: Oak 76.0, Birch 71.2, Maple 68.1.) In `adk run` the file lands in `agent45_data_analyst/.adk/artifacts/` (look there); in `adk web` it appears in the UI (not checked).
Learn: a result that is not text (a picture, a spreadsheet) is saved as an artifact (agent23), and the model only receives the file name and the numbers. Drawing the chart is plain code, so the bars are exactly right.

## Case 6: follow-up questions
In one chat: "Who improved the most from test1 to test3?" then "And what is the average of that improvement for class Oak?"
Expect: the second answer uses the `improvement` column from the first. Not run as a two-turn chat by hand; the test script asks each question in a fresh session, and the two improvement questions in it were answered correctly on both models in `tools` mode, which needs the improvement column.
Learn: `derive_column` stores the formula in session state (`state["derived"]`), and `frame()` rebuilds the table with those columns for every tool call, so a derived column lasts for the whole chat and needs no copy of the table.

## Case 7: what to take away
| | `none` | `tools` | `code` |
|---|---|---|---|
| exact numbers | no (3/7 and 6/7) | yes (7/7) | yes (7/7) |
| a question you did not foresee | answers anyway (maybe wrongly) | only what the tools can do | yes |
| control over what runs | n/a | full | little |
| table size | tiny (it is in the prompt) | any | tiny here (pasted in) |
| local models | yes | yes | no |

Learn: a small test (7 questions, one run each) is enough to see that the table-in-the-prompt approach is unreliable, not to rank `tools` and `code`: both got everything right.
