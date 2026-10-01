# agent08_workflow: cases, easiest first

Run: `uv run adk run agent08_workflow`, or `uv run adk web` to see each step and the state.
Concept: a workflow agent (`SequentialAgent`) that runs sub-agents in a fixed order.
Topic: a study helper that explains a topic, writes a quiz, then gives the answers.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT08_MODEL_PROVIDER` for this agent only.

## How it executes
Control: FIXED ORDER, set in code. No LLM decides what runs next. The same path every time.

```
 user topic
     │
     ▼
 ┌───────────┐  state["explanation"]  ┌─────────────┐  state["quiz"]  ┌────────────┐
 │ explainer ├───────────────────────►│ quiz_writer ├────────────────►│ answer_key │
 └───────────┘                        └─────────────┘                 └─────┬──────┘
   step 1                                step 2                             │ step 3
                                                                            ▼
                                                              state["answers"] + reply
 Each step waits for the one before it.
```

## Case 1: the whole pipeline runs
> photosynthesis

Expect: three replies in order: `[explainer]`, `[quiz_writer]`, `[answer_key]`.
Learn: one user message triggers all the sub-agents, with no extra prompting.

## Case 2: each step uses the previous step's output
Read the quiz questions and the answers against the explanation.
Expect: the questions only ask about things the explanation said, and the answers match it.
Learn: `output_key` saves a reply in session state, and `{explanation}` in a later
instruction is replaced with that saved value.

## Case 3: the order never changes
> the French Revolution
> how a bicycle stays upright

Expect: explainer, then quiz_writer, then answer_key, every time.
Learn: no model decides the order, unlike the coordinator in agent07.
Workflow agents give predictable control. Use them when the steps are always the same.

## Case 4: look at the state
Run `uv run adk web`, send a topic, open the session State.
Expect: `explanation`, `quiz` and `answers` are stored.
Learn: this is how agents hand data to each other, the same mechanism as `output_key` in agent06.

## Case 5: a vague or odd input
> stuff

Expect: the pipeline still runs all three steps and may produce a thin or invented explanation.
Learn: a workflow does not check the quality of its input. A wrong or empty early step
passes into every later step. Validation is something you add on purpose.

## Case 6: compare with agent07
Ask agent07 "what is photosynthesis and then quiz me". Compare with this pipeline.
Expect: agent07 may do part of the job in a different order, and a coordinator is not a pipeline.
Learn: use a coordinator (LLM decides) when the path varies. Use a workflow agent when it is fixed.

## Case 7: switch the model
    AGENT08_MODEL_PROVIDER=local  uv run adk run agent08_workflow
    AGENT08_MODEL_PROVIDER=gemini uv run adk run agent08_workflow

Expect: the same three steps. Gemini is usually faster and more careful about "use only the explanation".
Learn: the pipeline is independent of the model behind it.
