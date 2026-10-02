"""A tiny app that uses the capstone over HTTP: log in, ask, book a room, and approve the booking. Only `httpx`, no ADK.

Terminal 1 (from the project root), the server with a database, so bookings and preferences survive a restart (agents 34, 44):
    uv run adk api_server --port 8005 --session_service_uri sqlite+aiosqlite:///agent50_capstone/library.db agent50_capstone
Terminal 2:
    uv run python agent50_capstone/client.py                 asks you to approve the booking (y/n)
    uv run python agent50_capstone/client.py --yes           approves automatically

What it shows: the APP decides who the user is (the role goes into the session state when the session is created), and a person's
approval travels back to the agent as an ordinary message: a function response to the `adk_request_confirmation` call.
"""
import sys
from datetime import date, timedelta

import httpx

BASE, APP = "http://127.0.0.1:8005", "agent50_capstone"
USER, LOGIN = "alma", {"role": "student", "user_name": "Alma"}   # in a real app: from your login system, never from the chat
DAY = next(d for d in (date.today() + timedelta(days=n) for n in range(1, 8)) if d.weekday() in (1, 2, 3, 4)).isoformat()


def run(http: httpx.Client, session_id: str, parts: list[dict]) -> list[dict]:
    body = {"appName": APP, "userId": USER, "sessionId": session_id, "newMessage": {"role": "user", "parts": parts}}
    return http.post("/run", json=body).json()


def reply_text(events: list[dict]) -> str:
    texts = ["".join(p.get("text", "") for p in e.get("content", {}).get("parts", [])) for e in events]
    return next((t for t in reversed(texts) if t), "(no text)")


def confirmation_call(events: list[dict]) -> dict | None:
    for e in events:
        for p in e.get("content", {}).get("parts", []):
            call = p.get("functionCall")
            if call and call["name"] == "adk_request_confirmation":
                return call
    return None


with httpx.Client(base_url=BASE, timeout=300) as http:
    session = http.post(f"/apps/{APP}/users/{USER}/sessions", json={"state": LOGIN}).json()
    print(f"1. logged in as {LOGIN['user_name']} ({LOGIN['role']}), session {session['id'][:8]}")

    events = run(http, session["id"], [{"text": "Can I eat in the study rooms?"}])
    print("2. question ->", reply_text(events))

    events = run(http, session["id"], [{"text": f"Book Room A on {DAY} from 15:00 for 1 hour for 2 people."}])
    call = confirmation_call(events)
    if call is None:
        print("3. booking ->", reply_text(events), "(no approval was requested)")
        sys.exit()
    tool = call["args"].get("originalFunctionCall", {})
    print(f"3. the agent asks for approval: {tool.get('name')}({tool.get('args')})")
    approved = "--yes" in sys.argv or input("   approve? [y/n] ").strip().lower() == "y"
    answer = {"functionResponse": {"id": call["id"], "name": "adk_request_confirmation", "response": {"confirmed": approved}}}
    events = run(http, session["id"], [answer])
    print(f"4. {'approved' if approved else 'rejected'} ->", reply_text(events))

    state = http.get(f"/apps/{APP}/users/{USER}/sessions/{session['id']}").json()["state"]
    print("5. bookings stored by the app:", state.get("app:bookings") or "none")
