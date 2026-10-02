"""Talk to an agent over HTTP, the way a website or a phone app would. No ADK needed here: only `httpx`.

Start the server first (terminal 1, from the project root):
    uv run adk api_server --port 8004 agent44_serving
Then run this (terminal 2):
    uv run python agent44_serving/client.py                 prints each step
    uv run python agent44_serving/client.py "What is the capital of Peru?"

The steps: 1. ask the server which agents it has   2. create a session   3. send a message and read the events
           4. send a second message in the same session   5. do the same with a live stream of events (/run_sse)
"""
import json
import sys

import httpx

BASE = "http://127.0.0.1:8004"
APP, USER = "agent44_serving", "student-1"


def message(text: str) -> dict:
    return {"role": "user", "parts": [{"text": text}]}


def final_text(events: list[dict]) -> str:
    """The reply is in the last event that has text from the agent (earlier events hold tool calls and tool results)."""
    texts = ["".join(p.get("text", "") for p in e.get("content", {}).get("parts", [])) for e in events]
    return next((t for t in reversed(texts) if t), "")


with httpx.Client(base_url=BASE, timeout=300) as http:
    print("1. GET /list-apps ->", http.get("/list-apps").json())

    session = http.post(f"/apps/{APP}/users/{USER}/sessions", json={}).json()
    print("2. POST .../sessions -> session id", session["id"])

    question = sys.argv[1] if len(sys.argv) > 1 else "What is the capital of Japan?"
    events = http.post("/run", json={"appName": APP, "userId": USER, "sessionId": session["id"], "newMessage": message(question)}).json()
    kinds = []
    for e in events:
        for p in e.get("content", {}).get("parts", []):
            kinds.append("tool call " + p["functionCall"]["name"] if "functionCall" in p else "tool result" if "functionResponse" in p else "text")
    print(f"3. POST /run {question!r} -> {len(events)} events: {kinds}")
    print("   reply:", final_text(events))

    events = http.post("/run", json={"appName": APP, "userId": USER, "sessionId": session["id"],
                                     "newMessage": message("And Canada?")}).json()
    print("4. same session, second question ->", final_text(events))

    print("5. POST /run_sse (events arrive one by one):")
    with http.stream("POST", "/run_sse", json={"appName": APP, "userId": USER, "sessionId": session["id"],
                                               "newMessage": message("What is the capital of Kenya?"), "streaming": True}) as stream:
        count = 0
        for line in stream.iter_lines():
            if line.startswith("data:"):
                count += 1
                event = json.loads(line[5:])
                parts = event.get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                kind = "tool call" if any("functionCall" in p for p in parts) else "tool result" if any("functionResponse" in p for p in parts) else "text"
                print(f"   event {count}: {kind:<11} partial={event.get('partial')} {text[:60]!r}")
