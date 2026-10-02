# agent34_persistent_sessions: cases, easiest first

Concept: persistent sessions. A session (agent05) is a conversation plus its state. Here sessions are stored in a database file, so a conversation can
be continued later, by its id, even after the program has stopped. The second idea is state SCOPES: a key's prefix decides who can see it.

| key | scope | here |
|---|---|---|
| `chat_topic` (no prefix) | this session only | what this conversation is about |
| `user:books` | every session of the same user | the user's reading log |
| `app:...` | every user of the app | not used here |
| `temp:...` | only the current turn, never saved | not used here |

Topic: a reading-log assistant. Tools: `log_book(title, rating)`, `get_reading_log()`, `set_chat_topic(topic)`.
Run: `chat.py` sends ONE message per command. Each command is a new program run, so anything remembered must come from the database
`agent34_persistent_sessions/sessions.db` (ignored by git; delete it to start again).

    uv run python agent34_persistent_sessions/chat.py --user lina "Hi! This chat is about holiday reading. I just finished Dune, 5 stars."
    uv run python agent34_persistent_sessions/chat.py --user lina --list
    uv run python agent34_persistent_sessions/chat.py --user lina --session <id> "Also finished The Hobbit, 4 stars. What is this chat about?"
    uv run python agent34_persistent_sessions/chat.py --user lina --show <id>

Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT34_MODEL_PROVIDER` for this agent only.

## How it executes
```
 command 1 (a program run)          sessions.db (SQLite)                     command 3 (a NEW session, same user)
 user lina, new session S1 ──────►  ┌─────────────────────────────────┐ ◄──── user lina, new session S2
 "finished Dune, 5 stars"           │ sessions     S1, S2 (lina), S3 (sam)│      "What books have I read?"
   log_book ─► user:books ────────► │ events       every message of S1, S2 │      get_reading_log ─► reads user:books
   set_chat_topic ─► chat_topic ──► │ user_states  lina: {books: [...]}    │      ─► "Dune and The Hobbit"
                                    │ (session state of S1: chat_topic)   │      chat_topic? not in S2 ─► unknown
 command 2: --session S1 ─────────► └─────────────────────────────────┘
   continues S1: its history and its chat_topic are loaded again
```

## Case 1: start a session
    uv run python agent34_persistent_sessions/chat.py --user lina "Hi! This chat is about holiday reading. I just finished Dune, 5 stars."

Expect: `new session <id>` and a reply that Dune was logged. The program then exits.
Learn: the session, its messages and its state are now in `sessions.db`, not in the program's memory.

## Case 2: continue it later
Copy the id from `--list`, then:

    uv run python agent34_persistent_sessions/chat.py --user lina --session <id> "Also finished The Hobbit, 4 stars. What is this chat about?"

Expect: `continuing session <id> (6 earlier events)` (the number can differ), The Hobbit logged, and "This chat is about holiday reading".
Learn: the earlier messages were loaded from the database, so the model sees the whole conversation again. Same session id, same conversation.

## Case 3: a new session for the same user
    uv run python agent34_persistent_sessions/chat.py --user lina "What books have I read? And what is this conversation about?"

Expect (Gemini, from testing): "You have read Dune (rated 5 out of 5) and The Hobbit (rated 4 out of 5). I don't know what this conversation is about."
Learn: `user:books` belongs to Lina, so every one of her sessions sees it. `chat_topic` has no prefix, so it stayed in the first session.
(The local model answered "This conversation is about your reading history": a guess, not something stored.)

## Case 4: another user
    uv run python agent34_persistent_sessions/chat.py --user sam "What books have I read?"

Expect: "You haven't logged any books yet." (both models, in testing).
Learn: `user:` state is per user. Sam's sessions cannot see Lina's reading log.

## Case 5: look at what is stored
    uv run python agent34_persistent_sessions/chat.py --user lina --list
    uv run python agent34_persistent_sessions/chat.py --user lina --show <id>

Expect (Gemini, from testing): two sessions for Lina. The first has `chat_topic: 'holiday reading'` and both books; the second has only the books.
`--show` prints the stored conversation, message by message.
Learn: the database holds every message and all state. It is personal data, like agent21's memory, so it is kept out of git and should be protected
and deletable in a real system.

## Case 6: the database itself
    uv run python -c "import sqlite3; c = sqlite3.connect('agent34_persistent_sessions/sessions.db'); print([r[0] for r in c.execute('select name from sqlite_master where type=\"table\"')])"

Expect: tables including `sessions`, `events`, `user_states` and `app_states`.
Learn: ADK stores sessions, events and the different state scopes in separate tables. Production systems use the same service with another
database, for example PostgreSQL, by changing the `db_url`.

## Case 7: saying is not doing (local model)
Run case 1 with `MODEL_PROVIDER=local`, then `--list`.
Expect (from testing): the reply said "I've noted that as the topic", but the stored state had no `chat_topic` at all: `set_chat_topic` was never called.
In the continued session it still knew the topic, because the earlier message was in the history.
Learn: the same lesson as agent29: check the stored state, not the reply. Here `--list` shows the truth.

## Case 8: `adk run` can save and resume too
`uv run adk run` starts a new session every time. To keep one, save it to a file when you exit, and resume from that file later:

    uv run adk run --save_session --session_id my-chat agent34_persistent_sessions
    uv run adk run --resume agent34_persistent_sessions/my-chat.session.json agent34_persistent_sessions

Expect (Gemini, from testing): on exit, "Session saved to .../my-chat.session.json". With `--resume`, the earlier conversation is shown again and
"What books have I read?" is answered from it.
Learn: this is a file per conversation, handy for trying things out. `chat.py` shows the database approach that a real app would use: many users,
many sessions, all in one place. (`*.session.json` files are ignored by git.)
