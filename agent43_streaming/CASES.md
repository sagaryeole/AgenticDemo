# agent43_streaming: cases, easiest first

Concept: streaming. A model writes a reply piece by piece, about a word at a time. Without streaming the app waits until the whole reply is finished and shows it at once.
With streaming the app receives the pieces as they are written, so the user starts reading almost immediately. The total work is the same; what changes is how long the
user waits for the FIRST word. In ADK this is a setting on the run: `RunConfig(streaming_mode=StreamingMode.SSE)`.
Topic: a storyteller that answers every request with a story of about 150 words (long enough to feel the wait).
Run: `uv run python agent43_streaming/stream_demo.py` prints one request both ways with timings, and `--watch` prints the story live.
Use `MODEL_PROVIDER=local` in front for the local model. (`agent.py` is the agent; the script is what turns streaming on.)
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT43_MODEL_PROVIDER` for this agent only.

## How it executes
```
 NO STREAMING                                      STREAMING (SSE = server-sent events)
 app ── request ──► model                          app ── request ──► model
         ...the model writes 150 words...                  "Unit"  ──► event (partial=True)   ─► app shows "Unit"
         ...the user sees nothing...                       " 734,"  ──► event (partial=True)   ─► app shows " 734,"
 app ◄── ONE event with the whole text                     ...                                    (a few or hundreds of events)
         (partial=False) ─► app shows it                   whole text ► final event (partial=False) ─► app already showed it
                                                                                                    (use it for storing, not for printing again)
 first text at 13 s (local)                         first text at 0.9 s (local)
```

## Case 1: compare the two
Run the demo. Expect (from testing):

| | no streaming: first text | no streaming: all text | streaming: first text | streaming: all text | partial events |
|---|---|---|---|---|---|
| local `qwen3.5-9b` | 13.0 s | 13.0 s | **0.9 s** | 11.5 s | 217 |
| Gemini (4 runs) | 3.5 to 5.3 s | the same | 2.1 to 3.5 s | 3.8 to 5.1 s | 5 |

Learn: with the slow local model the user waits 13 seconds for a blank screen, or 1 second until the story starts to appear. Gemini answers this short story in about
4 seconds, so the gain is smaller (about a second or two); streaming matters more the longer and slower the reply is. The total time hardly changes, and the number of tokens is the same.

## Case 2: watch it happen
    uv run python agent43_streaming/stream_demo.py --watch
Expect: the story appears in pieces. Local: word by word. Gemini: in 5 chunks of a few sentences each.
Learn: how fine the pieces are depends on the model service, not on ADK. A chat screen should simply show each piece as it arrives.

## Case 3: partial events versus the final event
Read `run_once` in `stream_demo.py`: it checks `event.partial`.
Expect: the many events with `partial=True` hold small pieces of text. The last one has `partial=False` and holds the WHOLE text again.
Learn: a common mistake is to print every event: the user then sees the story twice (once in pieces, once complete). Show the partial events as they come, and use the final event for
what needs the complete text, such as saving it to a database or handing it to another step.

## Case 4: Gemini streams in big chunks
Expect (from testing): 5 partial events for about 180 words, and a first chunk after 2 to 3.5 seconds.
Learn: "streaming" does not promise small pieces. With Gemini 2.5, part of the first delay is the model's thinking before it writes anything, and the pieces that follow are
paragraph-sized. The local model, which is slower but sends token by token, feels more "live".

## Case 5: what streaming cannot do
Learn: streaming shows text sooner; it does not make the model faster, cheaper or better. It also makes the app code a little harder: you handle many events, you must tell partial from final,
and a reply that includes a tool call does not stream the tool call, only the text around it (not tested here). It is worth it for chat screens and long answers; for a program that just needs
the final answer, leave it off (the default).

## Case 6: not verified
`adk web` (the browser chat) has its own streaming setting, and live voice or video streaming with `connect()` (Gemini Live) is a different feature that needs a microphone and a model that
supports it. Neither was tested here. The SSE streaming in this agent is the part that works with any text model.
