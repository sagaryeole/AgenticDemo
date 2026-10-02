# agent32_openapi_tools: cases, easiest first

Concept: tools generated from an API description. Many services describe their REST API in a standard format called OpenAPI: every endpoint,
its parameters and what it returns. ADK's `OpenAPIToolset` reads that description and creates one tool per endpoint, so you write no tool
functions at all. When the model calls a tool, a real HTTP request goes to the service.
Topic: a to-do list. `todo_api.py` is a small to-do web service (built with FastAPI, which writes its own OpenAPI description). It knows nothing
about AI. The agent manages your list through it.
Two terminals, both from the project root:

    # Terminal 1: the to-do service
    uv run uvicorn agent32_openapi_tools.todo_api:api --port 8002

    # Terminal 2: the agent
    uv run adk run agent32_openapi_tools

Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT32_MODEL_PROVIDER` for this agent only.
The agent prints `[api call] ...` before each request. The service starts with two tasks: 1 "Return library books" (due 2026-10-05) and
2 "Call the dentist". Its data lives in memory, so restarting the service resets it.

## How it executes
```
 todo_api.py (the service)                      agent.py
 ┌──────────────────────────────┐   saved as    ┌───────────────────────────────────────────────┐
 │ GET    /tasks       list_tasks│──────────────►│ todo_openapi.json                             │
 │ POST   /tasks       add_task  │ (the OpenAPI  │      │                                        │
 │ POST   /tasks/{id}/complete   │  description) │      ▼                                        │
 │ DELETE /tasks/{id}            │               │ OpenAPIToolset ─► tools: list_tasks, add_task, │
 └──────────────▲───────────────┘               │                  complete_task, delete_task   │
                │                               └──────────────────────┬────────────────────────┘
                │   real HTTP request, e.g. POST /tasks/2/complete     │ the LLM picks a tool and its arguments
                └──────────────────────────────────────────────────────┘
```

## Case 1: look at the description first
With the service running, open `http://localhost:8002/docs` in a browser. Then open `todo_openapi.json` in this folder.
Expect: the docs page lists the four endpoints, and you can try each one with a button. The JSON file is the same description: each endpoint
has an `operationId` (`list_tasks`, `add_task`, `complete_task`, `delete_task`), a summary and its parameters.
Learn: the `operationId` becomes the tool's name, and the summary and parameters become what the model reads. The API's authors wrote the
tool descriptions without knowing it.

## Case 2: read through the API
> What is on my to-do list?

Expect: `[api call] list_tasks({})`, and the two starting tasks. The service terminal shows `"GET /tasks HTTP/1.1" 200 OK`.
Learn: the agent's tool call became a real HTTP request. Both Gemini and the local model did this in testing.

## Case 3: change data
> Add "Buy milk" due 2026-10-04.
> I called the dentist, mark it as done.

Expect: `add_task({'title': 'Buy milk', 'due': '2026-10-04'})`, then `complete_task({'task_id': 2})`. The service log shows `POST /tasks 201 Created`
and `POST /tasks/2/complete 200 OK`. Check in a browser: `http://localhost:8002/tasks`.
Learn: the model found the task id itself (2, from the earlier list) and put the right values in the right places: the title in the request body,
the id in the URL path.

## Case 4: query parameters
> Show me only the open tasks.

Expect: `list_tasks({'done': False})`, and the service log shows `GET /tasks?done=false`. Both models used the filter in testing.
Learn: the model read the parameter description ("Set done=false for open tasks only") from the API description and used it.

## Case 5: an error from the service
> Delete task 99.

Expect: `delete_task({'task_id': 99})`, the service answers `404 Not Found`, and the agent says there is no task 99. The local model did this in testing.
Learn: errors come back from the service like any result, so the agent can explain them. The service checks the data, not the model.

## Case 6: the service is down
Stop the service (Ctrl+C in terminal 1) and ask "What is on my to-do list?".
Expect: `[api error] list_tasks: ConnectError`, then a reply such as "I couldn't retrieve your to-do list. I was unable to connect to the to-do
service. Please make sure it's running." (both models, in testing).
Learn: without help, a failed HTTP request is an exception that stops the whole run: the first version of this agent crashed with a
`ConnectError` traceback and the user got no answer at all. `on_tool_error_callback=report_tool_error` in `agent.py` turns the exception into an
ordinary error result that the model can explain. The description saved in a file says nothing about whether the service is running.

## Case 7: change the API, not the agent
In `todo_api.py`, add a new endpoint, for example `GET /tasks/overdue` with `operation_id="list_overdue_tasks"`. Restart the service, then run
`uv run python agent32_openapi_tools/todo_api.py` to save the new description, and restart the agent.
Learn: the new tool appears without any change to `agent.py`. This is the same idea as MCP (agent12), but using an ordinary web API standard
that many existing services already publish.

## Case 8: OpenAPI, MCP or your own function?
| | Function tool (agent04) | MCP (agent12) | OpenAPI (agent32) |
|---|---|---|---|
| Tools are described by | your docstring | the MCP server | the API's OpenAPI description |
| The call goes to | your Python code | an MCP server | any REST web service |
| Good for | your own small logic | tools built for AI agents | existing web services you do not control |

Learn: if a service already has an OpenAPI description, you can give an agent access to it in a few lines. Be careful what you expose: every
endpoint becomes something the model can call, including `delete_task`. Use `tool_filter` to allow only some of them, and confirmation
(agent15) for risky ones.
