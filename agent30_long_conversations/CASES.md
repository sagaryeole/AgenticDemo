# agent30_long_conversations: cases, easiest first

Concept: the model has no memory of its own. On every call ADK sends the whole conversation so far, so each call gets bigger, slower and more
expensive. This agent compares three ways to handle a long conversation:

| `CONTEXT_MODE` | What is sent to the model on each call |
|---|---|
| `full` | the whole conversation (what every agent so far did) |
| `trim` | only the last 3 turns; older turns are simply left out |
| `compact` | older turns are replaced by a short summary that the model writes (ADK's `EventsCompactionConfig`) |

Topic: a friendly cooking helper. In turn 1 the user says "I'm Lina. I'm allergic to peanuts, and my cat is called Pepper." Then come 12 cooking
questions, and in turn 14: "Remind me: what is my name, what am I allergic to, and what is my cat called?"
Run the measurement script (one fixed 14-turn conversation, prompt tokens per turn, and the memory test at the end):

    uv run python agent30_long_conversations/long_chat.py --mode full
    uv run python agent30_long_conversations/long_chat.py --mode trim
    uv run python agent30_long_conversations/long_chat.py --mode compact

Add `MODEL_PROVIDER=local` in front for the local model (a few minutes per run). You can also chat by hand:
`CONTEXT_MODE=trim uv run adk run agent30_long_conversations`.

## How it executes
```
 turn 14 sends ...

 full:     [instruction] [turn 1] [turn 2] [turn 3] ... [turn 12] [turn 13] [turn 14]          grows every turn
 trim:     [instruction]                                [turn 12] [turn 13] [turn 14]          stays small, turn 1 is gone
 compact:  [instruction] [summary of turns 1-9 ] [turns 10-14 ...]                              summaries replace old turns
                           ▲
                           └── written by the model every 3 turns: "Lina, allergic to peanuts, cat Pepper, asked about ..."
```

## Case 1: the conversation grows
    uv run python agent30_long_conversations/long_chat.py --mode full

Expect (Gemini, from testing): prompt tokens rise steadily from 86 in turn 1 to 1,216 in turn 14, about 85 more per turn. The final answer
remembers all three facts (Lina, peanuts, Pepper). Local: 101 to 1,327 tokens, also 3 of 3.
Learn: the model "remembers" turn 1 only because turn 1 is sent again with every call. That is also why each call costs more than the last.
Here the answers are short (under 80 words); with long answers, documents or images (agent28) the growth is much faster.

## Case 2: cut the history, and lose facts
    uv run python agent30_long_conversations/long_chat.py --mode trim

Expect (from testing): prompt tokens stop growing at about 220-280. But turn 1 is no longer sent, so the facts are gone:
- Gemini remembered only the name (1 of 3) and said: "You haven't mentioned any allergies to me yet, nor have you told me your cat's name."
- Local remembered nothing (0 of 3), and called the user "Alex", a name that was never mentioned.
Learn: trimming is cheap and simple, but whatever falls out of the window is forgotten, and the model may even answer with confidence that
it was never said. For a peanut allergy that is a dangerous answer. Never trim away facts that matter.

## Case 3: summarise instead of cutting
    uv run python agent30_long_conversations/long_chat.py --mode compact

Expect (from testing): all three facts remembered on both models. Gemini's prompt tokens grew more slowly, to 866 in turn 14 instead of 1,216
(about 30% less). On the local model compaction gave no saving here (1,328, the same as `full`).
Learn: the summary kept the important facts while older turns were dropped. Whether it saves tokens depends on the conversation: here each
summary was about 900 characters, roughly as long as the short turns it replaced. With longer turns, a summary saves much more.

## Case 4: a summary can be wrong
Compaction happens every 3 turns (`compaction_interval=3`) and keeps 1 turn of overlap (`overlap_size=1`). A check of the summaries after 7 turns
found 2 summaries on each model, about 900 characters each. One local summary began: "...planning a peanut-free breakfast menu for the user (Lina)
and her dog (Pepper)". The cat had become a dog.
Learn: the summary is written by a model, so it can drop or change facts, and the original turns are no longer sent. Summaries also cost extra
model calls that the prompt-token numbers in cases 1-3 do not show. Important facts are safer stored explicitly, in state or memory (agent05, agent21).

## Case 5: try it by hand
    CONTEXT_MODE=trim uv run adk run agent30_long_conversations

Tell it your name and an allergy ("Hi, I'm Lina and I'm allergic to peanuts."), ask for a breakfast, lunch, dinner and snack idea, then ask
"What am I allergic to?"
Expect: it may still know! In testing Gemini answered "you mentioned you have a peanut allergy", although turn 1 was no longer sent. Its own
recent answers kept repeating the name and offering peanut-free food, so the fact was carried forward inside the last 3 turns.
Learn: a fact survives trimming only by luck, if the model happens to keep repeating it. In the 14-turn script (case 2) it was lost. Change
`KEEP_TURNS = 3` in `agent.py`, and ask questions where the fact does not come up naturally (for example about pasta shapes), to see forgetting.

## Case 6: which to choose
| | full | trim | compact |
|---|---|---|---|
| Remembers early facts | yes | no | usually (the summary can be wrong) |
| Cost per call | grows without limit | small and flat | grows slowly, plus summary calls |
| Complexity | none | a few lines (`keep_last_turns`) | an ADK setting, experimental |

Learn: for short chats, keep everything. For long ones, combine: keep recent turns, summarise older ones, and store facts that must never be lost
somewhere explicit, not in the conversation.
