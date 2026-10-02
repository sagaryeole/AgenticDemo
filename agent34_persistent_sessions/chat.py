"""Chat with the reading-log agent, one message per command, with sessions stored in a SQLite database file.

Every command is a NEW program run, so anything remembered between commands must have come from the database.

    uv run python agent34_persistent_sessions/chat.py --user lina "I just finished Dune, 5 stars."    # starts a new session
    uv run python agent34_persistent_sessions/chat.py --user lina --session <id> "Any sci-fi tips?"    # continues that session
    uv run python agent34_persistent_sessions/chat.py --user lina --list                               # lists Lina's sessions
    uv run python agent34_persistent_sessions/chat.py --user lina --show <id>                          # prints a session's history

The database is agent34_persistent_sessions/sessions.db (ignored by git). Delete it to start again.
"""
import argparse
import asyncio
from pathlib import Path

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from agent34_persistent_sessions.agent import root_agent

DB = Path(__file__).resolve().parent / "sessions.db"
APP = "reading_log"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--session", help="the id of a session to continue")
    parser.add_argument("--list", action="store_true", help="list this user's sessions")
    parser.add_argument("--show", metavar="SESSION_ID", help="print the stored history of a session")
    parser.add_argument("message", nargs="?")
    args = parser.parse_args()

    sessions = DatabaseSessionService(db_url=f"sqlite+aiosqlite:///{DB}")

    if args.list:
        found = (await sessions.list_sessions(app_name=APP, user_id=args.user)).sessions
        print(f"{len(found)} session(s) for {args.user}:")
        for s in found:
            full = await sessions.get_session(app_name=APP, user_id=args.user, session_id=s.id)
            print(f"  {s.id}   {len(full.events)} events   state: {full.state}")
        return

    if args.show:
        s = await sessions.get_session(app_name=APP, user_id=args.user, session_id=args.show)
        if s is None:
            print("No such session for this user.")
            return
        for e in s.events:
            text = " ".join(p.text for p in (e.content.parts if e.content and e.content.parts else []) if p.text)
            if text:
                print(f"  {e.author:>10}: {text[:120]}")
        return

    if args.session:
        session = await sessions.get_session(app_name=APP, user_id=args.user, session_id=args.session)
        if session is None:
            print(f"No session {args.session} for user {args.user}.")
            return
        print(f"continuing session {session.id} ({len(session.events)} earlier events)")
    else:
        session = await sessions.create_session(app_name=APP, user_id=args.user)
        print(f"new session {session.id}")

    runner = Runner(agent=root_agent, app_name=APP, session_service=sessions)
    reply = ""
    async for event in runner.run_async(user_id=args.user, session_id=session.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text=args.message)])):
        if event.author == root_agent.name and event.content and event.content.parts:
            reply = "".join(p.text or "" for p in event.content.parts) or reply
    print(f"agent: {reply.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
