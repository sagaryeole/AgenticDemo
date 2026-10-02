"""A tiny notes service that wants a secret token, like most real APIs. It knows nothing about AI.

Run (from the project root):  uv run uvicorn agent41_tool_auth.notes_api:api --port 8003
Save its OpenAPI description: uv run python agent41_tool_auth/notes_api.py       (writes notes_openapi.json next to this file)

Every request must carry the header  Authorization: Bearer <token>.  Without it, or with a wrong token, the answer is 401 Unauthorized.
The token is NOTES_API_TOKEN from the environment; the default below is a made-up demo value, not a real secret.
"""
import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

TOKEN = os.environ.get("NOTES_API_TOKEN", "demo-token-for-the-tutorial")

api = FastAPI(title="Notes API", version="1.0", servers=[{"url": "http://localhost:8003"}])
bearer = HTTPBearer(auto_error=False)   # we raise our own 401 below so the message is clear
NOTES = [{"id": 1, "text": "Buy a new notebook"}]


def require_token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if credentials is None or credentials.credentials != TOKEN:
        raise HTTPException(status_code=401, detail="Missing or wrong token")


class NewNote(BaseModel):
    text: str


@api.get("/notes", operation_id="list_notes", summary="List all notes", dependencies=[Depends(require_token)])
def list_notes():
    return NOTES


@api.post("/notes", operation_id="add_note", summary="Add a note", status_code=201, dependencies=[Depends(require_token)])
def add_note(note: NewNote):
    created = {"id": len(NOTES) + 1, "text": note.text}
    NOTES.append(created)
    return created


if __name__ == "__main__":
    target = Path(__file__).resolve().parent / "notes_openapi.json"
    target.write_text(json.dumps(api.openapi(), indent=2))
    print(f"saved {target}")
