# agent23_artifacts: cases, easiest first

Run: `uv run adk run agent23_artifacts`, or `uv run adk web` (the UI lists the saved files).
Concept: artifacts. An artifact is a named file (text, image, PDF...) that the agent produces and ADK stores with a version number.
Topic: a planning assistant that keeps a trip plan as a markdown document, and can bring back older versions.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT23_MODEL_PROVIDER` for this agent only.
The agent prints `[artifact] saved <file> version <n>` each time it saves. In `adk run` the files are real files here:
`agent23_artifacts/.adk/artifacts/` (look with `ls -R agent23_artifacts/.adk/artifacts`). Delete `.adk` to start clean.

## How it executes
Control: the LLM decides when to save, list or read. ADK stores the files and numbers the versions.

```
 "Make me a 2-day plan for Stockholm"        "Add a boat trip on day 2"             "Show me the first version"
        │                                            │                                       │
        ▼                                            ▼                                       ▼
   LLM writes the plan                      LLM: read_document("plan.md")            LLM: read_document("plan.md", version=0)
   save_document("plan.md", text)           (gets the current text, edits it)        gets the ORIGINAL text back
        │ saves                             save_document("plan.md", new text)
        ▼                                            │ saves                                 ▲
  ┌──────────────────────────────────────────────────▼──────────────────────────────────────┤
  │  artifact store            plan.md                                                         │
  │                              versions/0/plan.md   ◄── first save                           │
  │                              versions/1/plan.md   ◄── second save: a NEW version,           │
  │                                                      the old one is kept                   │
  └────────────────────────────────────────────────────────────────────────────────────────────┘
  names with the prefix  user:  are stored for the USER and can be seen from any session
```

## Case 1: create a document
> Make me a 2-day plan for visiting Stockholm.

Expect: an `[artifact] saved plan.md version 0 (...)` line, and a reply that names the file and the version. A file now exists under
`.adk/artifacts/.../plan.md/versions/0/`. (The local model chose its own name, `stockholm_plan.md`, in testing. The instruction says
to use `plan.md` unless the user names another file, and a model may not follow it.)
Learn: the agent's output is saved as a file, not just shown in the chat, so it can be opened, shared or kept.

## Case 2: every change is a new version
> Add a boat trip on day 2.
> Now drop the museum from day 1.

Expect: `saved ... version 1`, then `version 2`. In the folder you see `versions/0`, `versions/1` and `versions/2`, each with its own
copy of the text.
Learn: saving the same filename again does not overwrite. The older versions are kept, which gives you history for free.

## Case 3: list what exists
> What files do you have?

Expect: the filename (for example `plan.md`).
Learn: `list_artifacts` returns the names of the files that belong to this conversation (and any `user:` files).

## Case 4: go back to an older version
> Show me the very first version of the plan.

Expect: the original text, without the boat trip. Version 0 is the first save. Both Gemini and the local model did this correctly in
testing.
Learn: the old version is loaded from the store by its number, not from the model's memory of the conversation.

## Case 5: a new conversation starts without the files
Quit, start `uv run adk run agent23_artifacts` again, and ask "What files do you have?"
Expect: "I don't have any files saved yet." The first conversation's `plan.md` is still on disk, but it belongs to that session.
Learn: by default an artifact belongs to one session, like session state (agent05).

## Case 6: files that last across conversations
> Save a short packing list as user:packing.md with: passport, charger, umbrella.

Then quit, start again, and ask "What files do you have?" and "Show me user:packing.md".
Expect: `user:packing.md` is listed and readable in the new session. On disk it is under `.adk/artifacts/apps/.../users/test_user/artifacts/`,
separate from the per-session folders.
Learn: the `user:` prefix makes an artifact belong to the user instead of the session. Compare the three places data can live:
state (small values, one session), memory (facts, agent21) and artifacts (whole files, versioned).

## Case 7: saved does not mean correct
Read the plan the local model produced.
Expect: a nice-looking plan, with restaurant names such as "Restauranthotel Grand" and "Hästens Fika & Coffee" that the model
made up. The agent had no source to check them against.
Learn: an artifact store keeps whatever the model wrote, versioned and tidy, whether or not it is true. If the content must be
right, ground it first (agent20) or have a person review it (agent15).

## Case 8: look inside the files
Open `.adk/artifacts/.../plan.md/versions/1/plan.md` and the `metadata.json` next to it.
Expect: the plain text of that version, and a small file recording its type (`text/markdown`) and when it was saved.
Learn: the default storage is just files, so it is easy to inspect. Production setups store artifacts in cloud storage instead
(`--artifact_service_uri gs://bucket`).

## Case 9: other kinds of files
In `save_document`, the artifact is made with `types.Part.from_bytes(data=..., mime_type="text/markdown")`.
Learn: change the bytes and the type and the same call can store an image, a PDF or a CSV. The tool here only handles text.
(Not tested in this repo: images and PDFs.)
