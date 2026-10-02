# agent44_serving: cases, easiest first

Concept: serving an agent. So far you talked to agents in a terminal (`adk run`) or in the browser chat (`adk web`). A real product needs other programs to talk to the agent:
a website, a phone app, another service. For that, the agent runs behind an HTTP API, and anything that can send a web request can use it. ADK includes this server: `adk api_server`.
Nothing in `agent.py` knows about web servers. Serving is a matter of how you START the agent.
Topic: a geography quiz helper that knows six capital cities (one tool, `capital_of`).
Files: `agent.py` (the agent), `client.py` (a program that talks to the server with plain HTTP, only `httpx`), `Dockerfile` (packaging; NOT tested, see case 7).
Two terminals, both from the project root:

    # Terminal 1: the server (this folder becomes one "app" called agent44_serving)
    uv run adk api_server --port 8004 agent44_serving

    # Terminal 2: the client
    uv run python agent44_serving/client.py
    uv run python agent44_serving/client.py "What is the capital of Peru?"

Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT44_MODEL_PROVIDER` for this agent only (the server reads it when it starts).
In a browser, `http://127.0.0.1:8004/docs` lists every endpoint of the server with a button to try each one.

## How it executes
```
  client (any program)                                   adk api_server (FastAPI)                       your agent
  ───────────────────                                    ────────────────────────                       ──────────
  GET  /list-apps ────────────────────────────────────►  ["agent44_serving"]
  POST /apps/agent44_serving/users/student-1/sessions ─►  creates a session ─────────────► {id: "706c..."}   (state lives in the server)
  POST /run   {appName, userId, sessionId,
               newMessage: {role: user, parts: [{text: ...}]}} ─►  runs the agent ─► tool call, tool result, text   (all events, as a list)
  POST /run_sse  (same body) ───────────────────────────►  runs the agent ─► events one by one as they happen (agent43 streaming)
```

## Case 1: start the server and look around
Start terminal 1, then open `http://127.0.0.1:8004/docs`, and run `curl http://127.0.0.1:8004/health` and `curl http://127.0.0.1:8004/list-apps`.
Expect: `{"status":"ok"}` and `["agent44_serving"]`. The docs page lists endpoints such as `/run`, `/run_sse` and `/apps/{app_name}/users/{user_id}/sessions`.
Learn: the server already offers sessions, running, streaming, artifacts and memory as web endpoints. You wrote none of that.

## Case 2: one conversation, step by step
    uv run python agent44_serving/client.py
Expect (from testing, both models):
```
1. GET /list-apps -> ['agent44_serving']
2. POST .../sessions -> session id 706ca048-...
3. POST /run 'What is the capital of Japan?' -> 3 events: ['tool call capital_of', 'tool result', 'text']
   reply: The capital of Japan is Tokyo.
4. same session, second question -> The capital of Canada is Ottawa.
```
Learn: a "reply" is a list of EVENTS. The tool call and its result are events too, so a client can show "looking up the capital..." between the question and the answer. The final text is in the last event with text.
The session id ties the requests together: the second question is part of the same conversation, because the server keeps the session (agent05).

## Case 3: streaming over HTTP
Read step 5 of the client's output. Expect (from testing): events arrive one at a time. Local model: `text partial=True 'The'`, `' capital'` ... and a last event with `partial=False` holding the whole sentence.
Gemini: first `tool call`, `tool result`, then the text in a few chunks, then the final event.
Learn: `/run_sse` is the streaming version (agent43) of the same call, sent as server-sent events: lines that start with `data:`. A web page can read this with the browser's built-in `EventSource`.
Not every request calls the tool: on the local model, the third request in a session answered "The capital of Kenya is Nairobi" without calling `capital_of` in 3 of 3 runs (same effect as agent14: later turns copy the earlier replies);
in fresh sessions both `/run` and `/run_sse` called the tool 5 of 5 times. The answer was still right, but it did not come from the tool.

## Case 4: sessions that survive a restart
Stop the server, then start it with a database:

    uv run adk api_server --port 8004 --session_service_uri sqlite+aiosqlite:///sessions.db agent44_serving

Create a session and ask a question (client.py does both), stop the server, start it again with the same command, and list the sessions:
`curl http://127.0.0.1:8004/apps/agent44_serving/users/student-1/sessions`.
Expect (from testing): the session is still listed after the restart, with all 4 events. Delete `sessions.db` afterwards (database files are ignored by git).
Learn: this is agent34's database session service, switched on with one option. Without it, sessions only live as long as the server process (the default; not tested here).

## Case 5: the server has no login
Look at the first lines of `uv run adk api_server --help`: the endpoints are unauthenticated.
Expect (from testing): `client.py` needed no password or token.
Learn: anyone who can reach the port can run your agent (and spend your tokens) and read every session. The server is meant for a trusted network or for sitting BEHIND your own login layer (a reverse proxy, a gateway or your own FastAPI app).
By default it listens on `127.0.0.1`, which only your own machine can reach; `--host 0.0.0.0` opens it to the network. Compare agent41: there the API demanded a token; this is the API you would be protecting.

## Case 6: calling it from a web page
Expect: not tested. A page on another address needs `--allow_origins` (for example `--allow_origins "http://localhost:3000"`), otherwise the browser blocks the call (CORS).
Learn: the web page is just another HTTP client, doing what `client.py` does with `fetch()`.

## Case 7: the Dockerfile
`agent44_serving/Dockerfile` packages the agent into an image; `.dockerignore` (in the project root) keeps `.env`, `.venv` and databases out of it.
Expect: NOT tested. No Docker daemon was running while this agent was written (Docker's Colima VM was stopped), so the file was written from the documented commands only:

    docker build -f agent44_serving/Dockerfile -t quiz-agent .
    docker run --rm -p 8080:8080 quiz-agent

Learn: a container carries the agent and its libraries to any machine. Inside it, "127.0.0.1" means the container itself, so the local model is reached at `host.docker.internal`, the server must listen on `0.0.0.0`,
and Gemini needs credentials passed in (`docker run -e ...`), never copied into the image. If it fails when you try, that is useful information for improving the file.
