# agent12_mcp: cases, easiest first

Run: `uv run adk run agent12_mcp`, or `uv run adk web` to see the tool calls.
Concept: MCP (Model Context Protocol). The agent's tools live in a separate program and the agent
discovers them at startup, instead of having them written in its own code.
Topic: a librarian agent using a small library-catalogue MCP server (`library_server.py`).
Setup: needs the `mcp` package (`uv add mcp`, already done for this repo). No network and no LM Studio
is needed for the server itself.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT12_MODEL_PROVIDER` for this agent only.

## How it executes
Control: the LLM decides which tool to call, as in agent04. What is new is where the tools run.

```
  adk run agent12_mcp
        │ starts
        ▼
 ┌─────────────────────┐   1. start child process     ┌──────────────────────────┐
 │ ADK agent           ├─────────────────────────────►│ library_server.py        │
 │  McpToolset         │   2. "which tools do you     │  (MCP server, own process│
 │                     │      have?" ───────────────► │   talks over stdin/stdout)│
 │                     │◄─────── list_books,          │                          │
 │                     │         find_books_by_author,│  BOOKS = {...}           │
 │                     │         get_book             │                          │
 └─────────┬───────────┘                              └─────────────▲────────────┘
           │                                                        │
   user question                                                    │
           ▼                                                        │
        LLM sees the 3 tool schemas                                 │
           │ function_call: find_books_by_author("Tolkien")         │
           └──── 3. McpToolset forwards the call over MCP ──────────┘
                                                result goes back to the LLM ──► answer
```

## Case 1: a tool call through MCP
> Which books by Tolkien do you have, and are they available?

Expect: the answer lists "The Hobbit" (available) and "The Fellowship of the Ring" (not available).
Learn: it behaves like agent04, but nothing in `agent.py` defines these tools. They came from the server.

## Case 2: a different tool on the same server
> Tell me about book B003

Expect: `get_book` is called, and the answer is "Dune" by Frank Herbert, 1965, available.
Learn: one server can offer several tools, and the model picks per question.

## Case 3: nothing found
> Do you have anything by Stephen King?

Expect: the agent says there is none, and does not invent a title.
Learn: the instruction says "answer only from tool results". An empty result is still a result.

## Case 4: see the discovery step
Run `uv run adk web`, send case 1, and open the trace.
Expect: the model request includes three tool declarations that appear nowhere in `agent.py`.
Learn: `McpToolset` asks the server for its tool list at runtime. If the server gains a tool, the
agent can use it without a code change.

## Case 5: add a tool without touching the agent
Open `library_server.py`, add a new `@server.tool()` function (for example `books_after_year(year)`
returning books published after that year), save it, and ask:
> Which books were published after 1960?

Expect: the agent uses the new tool, with `agent.py` unchanged.
Learn: this is the point of MCP. The server and the agent are separate, so tools can be added or
changed in one place and any MCP-capable agent can use them.

## Case 6: limit what the model can use
In `agent.py`, enable the `tool_filter=["list_books", "get_book"]` line and ask case 1 again.
Expect: the agent can no longer search by author and falls back to listing or says it cannot.
Learn: `tool_filter` controls which of a server's tools reach the model. Do this when a server
offers more than the agent should be allowed to do. Remove the filter afterwards.

## Case 7: the server is just a program
Run it on its own: `uv run python agent12_mcp/library_server.py`.
Expect: it starts and waits silently, because it is waiting for MCP messages on stdin. Press Ctrl+C.
Learn: the agent starts it as a child process (`StdioServerParameters`). Other servers run elsewhere
and are reached over HTTP instead. That is a different connection type, same idea.

## Case 8: the model can only use what the tool returns
> List all the books you have, and which are available.

Expect: each book is shown with its correct availability (B002 and B005 are not available).
Learn: this agent originally failed here. `list_books` did not return `available`, the instruction
asked for availability, and Gemini guessed "Available" for every book, including one that is not.
The fix was in the server (return the field), not in the prompt. When a model states something
wrong, first check that the tool actually gave it that information. To see the failure, remove
`"available"` from `list_books` in `library_server.py` and ask again. Restore it afterwards.

Side note: a stdio server should not print to stdout, because stdout carries the protocol. With this
version of the `mcp` package a stray `print` was tolerated in testing, but do not rely on that.
Log to stderr instead.

## Case 9: compare function tools and MCP tools
| | Function tool (agent04) | MCP tool (agent12) |
|---|---|---|
| Where the code lives | in the agent's file | in a separate server |
| How the agent gets it | `tools=[my_function]` | `McpToolset(...)` finds them at startup |
| Reuse | one agent | any MCP client (many agents, other apps) |
| Cost | none | one more process to run and keep healthy |

Learn: use plain functions for small, private tools. Use MCP when tools are shared, owned by another
team, or already exist as an MCP server.
