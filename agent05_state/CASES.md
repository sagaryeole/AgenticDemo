# agent05_state: cases, easiest first

Run: `uv run adk run agent05_state` (LM Studio server must be running).
Type each line as a separate message in the same session.

## How it executes
Control: the LLM chooses the tool. The tools read and write session state, which lives
between messages in the same session.

```
 "remember X"                         "what did I note?"
      │                                     │
      ▼                                     ▼
    LLM ──► save_note(X)                  LLM ──► list_notes()
                 │ writes                              │ reads
                 ▼                                     ▼
        ┌────────────────────────────────────────────────┐
        │  SESSION STATE   notes = ["X", ...]            │
        └────────────────────────────────────────────────┘
   new session ──► state starts empty
```

## Case 1: one tool call
> Remember that the payments-api deploy is at 14:00.

Expect: `save_note` is called, the agent confirms.
Learn: the model picks a tool and fills its argument from your sentence.

## Case 2: state survives a turn
> What did I ask you to remember?

Expect: `list_notes` is called, the answer says "payments-api deploy at 14:00".
Learn: the answer comes from session state, not from the model's memory.

## Case 3: state accumulates
> Also note that orders-api has a disk alert.
> List everything you have noted.

Expect: both notes returned, `total_notes` goes to 2.
Learn: state is read, changed and written back each call.

## Case 4: nothing saved, no invention
Quit, start a new `adk run` and ask:
> What did I ask you to remember?

Expect: "nothing saved", with no made-up notes.
Learn: a new session starts with empty state. The instruction forbids invention,
so this also checks grounding.

## Case 5: persistence (try with `adk web`)
Run `uv run adk web`, pick agent05_state, add a note, then reload the same session.
Learn: sessions are stored (SQLite `.adk/session.db`); a new session is not the same
as the same session resumed.
