# agent29_dynamic_instructions: cases, easiest first

Run: `uv run adk run agent29_dynamic_instructions`
Concept: a dynamic instruction. Until now every instruction was a fixed string. Here the instruction is a FUNCTION (`build_instruction`)
that ADK calls before every model call. It reads session state, so the agent's behaviour can change during the conversation.
The second idea is a few-shot example: instead of only describing the answer format, the instruction SHOWS one finished answer.
Topic: a study helper that explains a topic at three levels: `kid`, `student` (the default) and `expert`.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT29_MODEL_PROVIDER` for this agent only.
Before each model call the agent prints `[instruction] level=... name=...`. With `SHOW_INSTRUCTION=1` it prints the start of the
instruction itself.

## How it executes
```
  every model call:
     session state  {"level": "kid", "name": "Lina"}
           │
           ▼
     build_instruction(ctx)  ──►  "You are a friendly study helper ...
                                   Current level: kid. Use short sentences and everyday words ...
                                   The user's name is Lina; greet them by name.
                                   Step 1, tools ... Step 2, three labelled parts ...
                                   Example of the required format: **In one line:** ... **Explanation:** ... **Check yourself:** ..."
           │
           ▼
         LLM ──► may call set_level("kid") or set_name("Lina") ──► state changes
                                                                       │
     the NEXT model call builds a new instruction from the new state ◄─┘
```

## Case 1: the default level
> What is photosynthesis?

Expect: `[instruction] level=student name=-`, then an answer in three labelled parts: **In one line:**, **Explanation:**, **Check yourself:**.
Learn: the format comes from the example in the instruction. The level comes from state, which is empty, so the default `student` is used.

## Case 2: the instruction changes during the conversation
In the same session:
> I am 10 years old and that was too hard. Can you explain it again?

Expect: the model calls `set_level`, and the next `[instruction]` line shows `level=kid`. The new explanation uses everyday words ("plants are like
little chefs"). Both Gemini and the local model did this in testing.
Learn: a tool changed state, and the very next model call got a different instruction. The behaviour changed without restarting anything.

## Case 3: personalising with stored values
> My name is Lina. What is gravity?

Expect: `[instruction] level=kid name=Lina`, and an answer that greets Lina and stays at kid level.
Learn: anything in state can shape the instruction: a name, a language, a level, a preference.

## Case 4: start with a known state
    uv run adk run --state '{"level": "expert", "name": "Sam"}' agent29_dynamic_instructions

Ask "What is photosynthesis?".
Expect: `[instruction] level=expert name=Sam` from the first call, and an expert answer that greets Sam.
Learn: state can be set from outside before the conversation starts. A real app would load it from a user profile.

## Case 5: saying is not doing
The first version of the instruction said "If the user tells you their age ... call set_level", followed by "Always answer in exactly three labelled
parts ... and nothing else". With that version the local model never called the tools. It replied "Your explanation level has been updated to
'expert'" and "Thanks, Lina! I'll remember that", while `[instruction]` still showed `level=student name=-`. Nothing had been saved.
The current instruction splits the work into "Step 1, tools: ... FIRST call set_level" and "Step 2, the answer", and adds "Saying you changed
something without calling the tool does not change it". With that, the local model called both tools in 2 of 2 test runs.
Learn: watch the state, not the reply. A model can claim an action it never performed. And an instruction that stresses one thing ("answer in
exactly three parts and nothing else") can crowd out another (calling a tool first). Order the steps clearly.

## Case 6: show, don't only tell (few-shot)
Ask three questions ("What is photosynthesis?", "What is a volcano?", "Why is the sky blue?"), then run again with `FEW_SHOT=0`, which removes
the example from the instruction and keeps only the sentence that names the three parts.

    FEW_SHOT=0 uv run adk run agent29_dynamic_instructions

Expect (from testing, three answers each):

| | with the example | `FEW_SHOT=0` |
|---|---|---|
| Gemini | exact labels, 3/3 | labels kept, but numbered "1. **In one line:**" |
| local | exact labels, 3/3 | "In one line" label missing in 3/3 answers |

Learn: one worked example fixed the format better than a description in words, especially on the smaller model. Examples are powerful, and
models copy them closely, including their length and tone, so choose them carefully.

## Case 7: look at the real instruction
    SHOW_INSTRUCTION=1 uv run adk run agent29_dynamic_instructions

Ask a question, then say you are 10.
Expect: the start of the full instruction is printed before each model call, and the "Current level" line changes after `set_level`.
Learn: when an agent behaves unexpectedly, look at the instruction it actually received. With a function, it can be different on every call.

## Case 8: a function or a template?
A fixed instruction can also contain `{level}`, which ADK fills from state (agent08 and agent10 use this). A function, as here, can contain any
logic: choose a whole block of rules, add a line only when a name exists, read a file. Note that when the instruction is a function, ADK does
not replace `{...}` placeholders in it; the function builds the text itself.
Learn: use a template for simple substitutions, and a function when the instruction needs decisions.
