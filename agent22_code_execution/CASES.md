# agent22_code_execution: cases, easiest first

Run: `uv run adk run agent22_code_execution`
Concept: language models are fluent but unreliable at exact work: big multiplication, compound interest, counting. Instead of
trusting the model's "head", let it use a program for the exact part. Three modes, chosen with `CODE_MODE`:

| `CODE_MODE` | How the answer is produced | Works with |
|---|---|---|
| `none` | the model alone (a baseline, to see the problem) | any model |
| `builtin` | Gemini writes Python and Google runs it in a sandbox (`BuiltInCodeExecutor`) | Gemini only |
| `calculator` | two small, safe tools: `calculate(expression)` and `count_letter(text, letter)` | any model |

Default: `builtin` with Gemini, `calculator` with a local model. `CODE_MODE=builtin` with a local model stops with a clear error.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT22_MODEL_PROVIDER` for this agent only.

Example: `CODE_MODE=none MODEL_PROVIDER=gemini uv run adk run agent22_code_execution`.
The six test questions are in case 1. Note that the local model with `CODE_MODE=none` can take several minutes: it works through
the long multiplication step by step.

## How it executes
```
 CODE_MODE=none                      CODE_MODE=builtin (Gemini)            CODE_MODE=calculator (any model)
 ──────────────                      ──────────────────────────            ────────────────────────────────
 question                            question                              question
    │                                   │                                     │
    ▼                                   ▼                                     ▼
   LLM                                 LLM writes code:                      LLM picks a tool:
 "does it in its head"                 print(48271 * 91357)                  calculate("48271 * 91357")
    │                                   │                                     │
    │                                   ▼                                     ▼
    │                              Google's sandbox RUNS it               your Python parses it safely
    │                                   │ output: 4409893747                  │ result: 4409893747
    │                                   ▼                                     ▼
    ▼                                  LLM reports the output               LLM reports the result
 a confident answer,                  an answer that comes from             an answer that comes from
 sometimes wrong                      a program                             a program
```

## Case 1: see the difference (the six questions)
Ask, in this order: "What is 48271 times 91357?", "How many times does the letter r appear in strawberry?", "What day of the week was
14 March 1999?", "What is 2 to the power of 100?", "If I invest 2500 dollars at 3.7 percent yearly interest, compounded monthly,
how much do I have after 12 years?", "Is 1000003 a prime number?"

True answers (computed with Python): 4,409,893,747 / 3 / Sunday / 1,267,650,600,228,229,401,496,703,205,376 / $3,894.66 / yes.

Expect (from testing):

| | multiplication | letters | weekday | 2^100 | interest | prime |
|---|---|---|---|---|---|---|
| Gemini, `none` | 4,410,940,747 wrong | 3 | Sunday | right | $3,895.89 wrong | yes |
| Gemini, `builtin` | right | 3 | Sunday | right | $3,894.66 | yes |
| local, `none` | 4,409,951,747 wrong | 3 | Sunday | right | $3,584.54 wrong | "not prime... wait, let me recalculate" |
| local, `calculator` | right (tool) | 3 (tool) | "cannot determine with these tools" | right (tool) | $3,894.66 (tool) | "cannot determine with these tools" |

Learn: without code, both models gave confident wrong numbers for the long multiplication and the compound interest, with no sign of
doubt. With a program, the numbers are right. The two questions the calculator cannot do are answered honestly as "cannot", not guessed.

## Case 2: the model is not always wrong
Look at the "none" rows for the letter count, the weekday and 2^100.
Expect: correct. Models have memorised common facts, and a strong model handles some arithmetic.
Learn: that is why the problem is dangerous. You cannot tell from the answer whether the model calculated or guessed. Use code
whenever the exact answer matters.

## Case 3: look at the code Gemini wrote
`adk run` prints only the final text. Run `uv run adk web` to see the steps, or in testing the event stream contained this:
`CODE: print(48271 * 91357)`, `OUTPUT: 4409893747`, then the text "The product of 48271 and 91357 is 4,409,893,747."
Learn: the answer is checkable. A reviewer can read the code and the output, which is not possible for a number the model "just knew".

## Case 4: the calculator is deliberately small and safe
The `calculate` tool does not use `eval`. It parses the expression and accepts only numbers, `+ - * / // % **`, parentheses and
`sqrt`, `round`, `abs`, `min`, `max`. In testing these inputs were all refused with an error message:
`__import__('os').system('echo HACKED')`, `open('/etc/passwd').read()`, `lambda: 1`, `9**9**9` ("exponent too large"), `2**100000`.
Division by zero and a missing bracket also returned a clear error.
Learn: text written by a model (or typed by a user) must never be passed to `eval`: it would run any Python code. Allow only
what you need. An `exponent too large` limit also stops an input that would freeze the program.

## Case 5: "builtin" runs in Google's sandbox, not on your machine
Learn: with `BuiltInCodeExecutor` the code runs on Google's side, isolated from your files and network. ADK also has
`UnsafeLocalCodeExecutor`, which runs model-written code in YOUR process, as the name warns. Do not use it with real data or
untrusted users. Containers (`ContainerCodeExecutor`) and cloud sandboxes are the safe options when you need a local or custom
environment. This tutorial does not run those.

## Case 6: a local model cannot use the built-in executor
Run `CODE_MODE=builtin MODEL_PROVIDER=local uv run adk run agent22_code_execution`.
Expect: a clear error at start-up: "CODE_MODE=builtin needs Gemini ... Use CODE_MODE=calculator for a local model."
Learn: built-in tools depend on the model (the same point as `google_search` in agent02). A local model needs tools you provide.

## Case 7: tools you provide are limited to what you wrote
Ask the calculator mode "What day of the week was 14 March 1999?" or "Is 1000003 a prime number?"
Expect: an honest "I cannot determine that using the available tools", because the instruction says not to calculate in its head.
Learn: a tool gives exactness but only for what it covers. Code execution is general (the model can write any program) and a
calculator is narrow (and so is easier to make safe). Choose by how much freedom you can safely give.

## Case 8: try it yourself
Add a tool to `agent.py`, for example `day_of_week(year, month, day)` using `datetime.date(...).strftime("%A")`, add it to
`tools=[...]` in calculator mode, and ask the weekday question again.
Learn: adding one small exact tool turns an honest "cannot" into a verified answer.
