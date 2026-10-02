# agent27_a2a: cases, easiest first

Concept: Agent-to-Agent (A2A). An agent in one program calls an agent in ANOTHER program over the network, using an open protocol.
Compare MCP (agent12), where an agent calls a TOOL in another program. Here the thing it calls is a whole agent, with its own model and instructions.
Topic: a shop assistant (client) that asks a separate shipping-quote agent (server) for prices.
Two programs, so you need TWO terminals, both from the project root:

    # Terminal 1: the remote agent (the server)
    uv run uvicorn agent27_a2a.remote_server:a2a_app --port 8001

    # Terminal 2: the shop assistant (the client)
    uv run adk run agent27_a2a

Each side picks its own model with `MODEL_PROVIDER`. They need not match: `MODEL_PROVIDER=gemini` for the server and
`MODEL_PROVIDER=local` for the client works. Server and client share only a URL (default `http://localhost:8001`, change it with
`SHIPPING_AGENT_URL`). The client never imports the server's code.
Needs the `a2a-sdk` package (it is in `pyproject.toml`, so `uv sync` installs it).
Tip: put `PYTHONUNBUFFERED=1` in front of the server command, so its `print` lines show up straight away.

## How it executes
Control: the LLM in the client decides when to hand over to the remote agent (as in agent07). The call itself goes over HTTP.

```
   TERMINAL 2 (client, one process)                            TERMINAL 1 (server, another process)
 ┌────────────────────────────────────┐                      ┌──────────────────────────────────────┐
 │ shop_assistant (LLM)               │                      │ uvicorn  ──  a2a_app = to_a2a(agent) │
 │    │ "shipping question → transfer"│                      │                                      │
 │    ▼                               │  1. GET /.well-known/agent-card.json                         │
 │ shipping_service = RemoteA2aAgent ─┼───────────────────────►  the AGENT CARD: name, description,   │
 │    (a stand-in for the remote one) │◄───────────────────────  skills, how to call it             │
 │                                    │  2. POST /   "How much to ship 3.5 kg to Europe?"            │
 │                                    ├───────────────────────►  shipping_agent (its own LLM)         │
 │                                    │                      │      │ tool: get_shipping_quote(...)   │
 │                                    │◄───────────────────────  "It costs $20.75"  ◄────────────────┘
 └────────────────────────────────────┘
```

## Case 1: look at the agent card
With the server running, open `http://localhost:8001/.well-known/agent-card.json` in a browser, or run
`curl http://localhost:8001/.well-known/agent-card.json`.
Expect: JSON with the agent's `name` ("shipping_agent"), `description`, `skills` (including its tool `get_shipping_quote`) and the URL to call.
Learn: the card is the agent's public business card. A client reads it to learn what the agent does and how to reach it, which is
why the client in `agent.py` needs only the card's URL.

## Case 2: a question the shop assistant answers itself
> What is the capital of France?

Expect: the answer comes from `[shop_assistant]`, and no question is sent to the server (no new `POST /` line in the server terminal).
Learn: the client only calls the remote agent when its own instruction says to.

## Case 3: a question for the remote agent
> How much does it cost to ship a 3.5 kg parcel to Europe?

Expect: `[shipping_service]: ... 20.75 dollars`. The price is correct: a base price of $12 plus $2.50 per kg for Europe is 12 + 2.5 × 3.5 = 20.75.
In the server terminal you see `[remote shipping agent] quote requested: 3.5 kg to europe` and a `POST /` request.
Learn: the user talked to the shop assistant, but the answer was computed by another program with its own tool. The `adk run`
output shows the remote answer twice (two events carry the same text). That is cosmetic.

## Case 4: a follow-up, and who is trusted
> And to the rest of the world, same parcel?

Expect with Gemini on both sides: `... to the rest of the world ... 39 dollars` (25 + 4 × 3.5 = 39). Correct.
Learn: the client transferred to the remote agent again, with the earlier context.

## Case 5: the remote agent can be wrong, and the caller cannot see it
Start the SERVER with the local model (`MODEL_PROVIDER=local`), and the client with Gemini, and repeat cases 3 and 4.
Expect (from testing): the Europe price was right, but for "the rest of the world" the remote agent answered `$25.50`. The correct
price is $39 (25 + 4 x 3.5), so the remote model did not get it from its tool: it guessed, or called the tool wrongly.
Learn: the client receives only text. It has no way to check whether the remote agent used its tool or guessed. When you call
another team's agent, you are trusting it. Return structured data and sources, or verify important values.

## Case 6: a small client model may not call at all
Start the client with the local model (`MODEL_PROVIDER=local uv run adk run agent27_a2a`) and repeat cases 3 and 4.
Expect (from testing, seen twice, once with a local and once with a Gemini server): the first question is handed over correctly, but for the follow-up `[shop_assistant]` answered itself,
repeating the Europe price ("20.75 dollars") instead of asking the shipping agent about the rest of the world.
Learn: the same habit as in agent10, agent20 and agent25: a small model copies its own earlier answer. A system is only as reliable
as the weakest model in the chain.

## Case 7: the remote agent is not running
Stop the server (Ctrl+C in terminal 1) and ask the shipping question again.
Expect: no answer at all. The program prints an `AgentCardResolutionError` into its log and you get the `[user]:` prompt back with nothing
said. In testing there was no friendly message.
Learn: across a network things fail: servers stop, ports change, timeouts happen. A production client handles that explicitly, for
example by catching the error and telling the user "the shipping service is unavailable".

## Case 8: swap in a different agent behind the same URL
Change the prices in `RATES` in `remote_server.py`, restart the server, and ask again. The client file is untouched.
Learn: that is the point of a protocol. The client depends on the card and the protocol, not on the server's code. The server could be
written in another language or by another company, as long as it speaks A2A.

## Case 9: A2A or MCP or agent-as-tool?
| | Agent as a tool (agent14) | MCP (agent12) | A2A (agent27) |
|---|---|---|---|
| What you call | an agent in the same program | a tool in another program | an agent in another program |
| The other side has | a model, in your process | no model, just functions | its own model, instructions and tools |
| Connection | a function call | stdio or HTTP | HTTP, with an agent card |
| Use when | splitting work inside one app | sharing tools between apps | agents owned by different teams or services must cooperate |

Learn: pick the lightest option that fits. Across a team or company boundary, A2A lets each side change its own agent without breaking the other.

## Case 10: what was not tested
Authentication (anyone who can reach port 8001 can call this agent), streaming responses and long-running tasks were not exercised.
Never expose a server like this to the internet without authentication.
