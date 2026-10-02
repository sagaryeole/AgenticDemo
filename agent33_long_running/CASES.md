# agent33_long_running: cases, easiest first

Concept: some work takes a long time: exporting a video, printing, a report, a payment check. An agent should not freeze while it waits.
Two patterns, one file each:
- `agent.py`, the **ticket pattern** (works in `adk run`): a tool STARTS the job and returns a job id at once; another tool reports progress.
  Run: `uv run adk run agent33_long_running`
- `resume_demo.py`, ADK's **pause and resume** (`LongRunningFunctionTool`): the conversation waits for a result, and the app sends that result
  in later. Run: `uv run python agent33_long_running/resume_demo.py`
Topic: exporting holiday videos (720p takes about 20 seconds, 1080p 40, 4k 90; the work is only pretended, using the clock), and a print shop.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT33_MODEL_PROVIDER` for this agent only.
The agent prints `[job] ...` lines when a job starts and when it is checked.

## How it executes
```
 TICKET PATTERN (agent.py)
   "Export my holiday video in 720p" ─► start_export ─► returns at once: {job_id: "job-1", estimated_seconds: 20}
   "What's 720p vs 1080p?"           ─► answered normally, the job keeps running in the background
   "Is it done?"                     ─► check_export("job-1") ─► {status: running, percent_done: 19, seconds_left: 16}
   ...later... "Is it done now?"     ─► check_export("job-1") ─► {status: done, file: holiday_720p.mp4}

 PAUSE AND RESUME (resume_demo.py)
   "Print report.pdf, 20 copies" ─► send_to_print_shop (a LongRunningFunctionTool) ─► {status: queued, ticket: P-17}
        the call stays OPEN, with an id ─────────────────────────────────────────┐
   ...the print shop finishes...                                                  │
   the APP sends  FunctionResponse(id = that id, response = {status: done, pickup: "desk 2"})
        ─► the agent continues: "Your 20 copies are ready for pickup at desk 2."
```

## Case 1: start a job, keep chatting
> Please export my holiday video in 720p.
> While that runs: what is the difference between 720p and 1080p?

Expect: `[job] job-1 started: holiday in 720p, takes about 20 s`, a reply with the job id and the estimated time, then a normal answer about
resolutions while the job runs.
Learn: the tool returned at once, so the conversation was never blocked. The slow part continues outside the model.

## Case 2: ask for progress
> Is my export finished?

Expect (if asked within 20 seconds): `[job] job-1 checked: 19%` (or another number) and "still running, 19% done, about 16 seconds left".
Ask again after 20 seconds: "done", with the file name `holiday_720p.mp4`.
Learn: progress comes from the tool, every time. In testing (Gemini, timed script) the agent reported 19% and then "done" exactly as the tool said.
The local model answers more slowly, so by the time the user asked (25 seconds in) the 720p job was already done. Use 4k to see progress there.

## Case 3: the agent must not pretend
Ask "Is it done?" straight after starting a 4k export (90 seconds).
Expect: "still running" with a percentage, not "done".
Learn: the instruction says "never say an export is finished unless check_export returned status 'done'". A model that guesses "it should be done
by now" would be wrong; the tool is the only source of truth.

## Case 4: several jobs
> Export my birthday video in 1080p, and my hiking video in 4k.
> Which exports do I have, and how far along are they?

Expect: two job ids, then two `check_export` calls with different percentages (in testing: 7% and 3%). The agent may also call `list_jobs`
first; in testing it did not need to, because the ids were still in the conversation.
Learn: job ids let the user and the agent refer to each job separately. They are stored in session state, so a new session will not know them;
a real system would store jobs in a database (see agent34).

## Case 5: pause and resume
    uv run python agent33_long_running/resume_demo.py

Expect (from testing, Gemini):

    1. The user asks for printing
       [print shop] received report.pdf x 20, ticket P-17
       agent: 'Your document has been queued with ticket number P-17. I will let you know when it is ready for pickup.'
       long-running calls still open: [('send_to_print_shop', 'adk-...')]
    2. ...time passes. The print shop finishes the job (3 seconds here).
    3. The app sends the final result back, using the SAME call id
       agent: 'Your 20 copies of report.pdf are ready for pickup at desk 2, ground floor.'

Learn: with `LongRunningFunctionTool`, ADK marks the call as still open (`event.long_running_tool_ids`). Your app keeps the call id, waits for the real
outcome (a person, a webhook, a queue) and sends it back as a `FunctionResponse` with that same id. The model then continues with the real result.

## Case 6: which pattern?
| | Ticket pattern (`agent.py`) | Pause and resume (`resume_demo.py`) |
|---|---|---|
| Who finds out the job is done | the user asks, the agent checks | your app sends the result in |
| Works in `adk run` | yes | needs app code |
| Good for | jobs the user wants to check on | results that arrive by themselves (approvals, callbacks, queues) |

Learn: both keep the conversation responsive. Choose by who learns first that the work is finished: the user or your system.
