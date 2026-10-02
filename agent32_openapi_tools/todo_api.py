"""A tiny to-do REST API, the "other team's service" that agent32 will use. It knows nothing about AI.

Start it in its own terminal, from the project root:

    uv run uvicorn agent32_openapi_tools.todo_api:api --port 8002

Then look at:  http://localhost:8002/docs          (a web page that lists the endpoints and lets you try them)
               http://localhost:8002/openapi.json  (the same description as JSON: this is what the agent reads)

To refresh the saved copy of the description that the agent loads:  uv run python agent32_openapi_tools/todo_api.py
"""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PORT = 8002
api = FastAPI(
    title="Todo API",
    version="1.0",
    description="A small to-do list service.",
    servers=[{"url": f"http://localhost:{PORT}"}],   # tells API clients (and the agent) where to send requests
)


class NewTask(BaseModel):
    title: str = Field(description="What needs to be done, e.g. 'Buy milk'.")
    due: str | None = Field(default=None, description="Optional due date as YYYY-MM-DD.")


class Task(NewTask):
    id: int
    done: bool = False


TASKS: dict[int, Task] = {
    1: Task(id=1, title="Return library books", due="2026-10-05"),
    2: Task(id=2, title="Call the dentist"),
}


# operation_id becomes the TOOL NAME the agent sees; summary and description become the tool's description.
@api.get("/tasks", operation_id="list_tasks", summary="List tasks",
         description="Returns all tasks. Set done=true for finished tasks only, done=false for open tasks only.")
def list_tasks(done: bool | None = None) -> list[Task]:
    return [t for t in TASKS.values() if done is None or t.done == done]


@api.post("/tasks", operation_id="add_task", summary="Add a task", status_code=201)
def add_task(task: NewTask) -> Task:
    new = Task(id=max(TASKS, default=0) + 1, **task.model_dump())
    TASKS[new.id] = new
    return new


@api.post("/tasks/{task_id}/complete", operation_id="complete_task", summary="Mark a task as done")
def complete_task(task_id: int) -> Task:
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail=f"No task with id {task_id}")
    TASKS[task_id].done = True
    return TASKS[task_id]


@api.delete("/tasks/{task_id}", operation_id="delete_task", summary="Delete a task")
def delete_task(task_id: int) -> dict:
    if TASKS.pop(task_id, None) is None:
        raise HTTPException(status_code=404, detail=f"No task with id {task_id}")
    return {"deleted": task_id}


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "todo_openapi.json"
    out.write_text(json.dumps(api.openapi(), indent=2))
    print(f"wrote {out.name} with operations: {[op['operationId'] for p in api.openapi()['paths'].values() for op in p.values()]}")
