# agent28_multimodal: cases, easiest first

Run: `uv run adk run agent28_multimodal`, and name an image in your message, for example "How many circles are in shapes.png?"
Concept: multimodal input. A message to a model is a list of PARTS. Text is one kind of part; an image is another (the bytes plus a
type such as `image/png`). Gemini and the local `qwen3.5-9b` (which has vision) can both read images.
Topic: three test images in `agent28_multimodal/images/`, drawn by `make_images.py` so the right answers are known exactly:
- `shapes.png`: 3 red circles, 2 blue squares, 1 green triangle.
- `receipt.png`: a café receipt. The items add up to 10.25, but the printed total says **11.25** (a deliberate mistake).
- `chart.png`: library visitors per day: Mon 120, Tue 95, Wed 150, Thu 80, Fri 135 (total 580).
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT28_MODEL_PROVIDER` for this agent only.

`adk run` only lets you type text, so `agent.py` has a callback that spots an image file name in your message and attaches that image
to the request. It prints `[image] attached receipt.png (16 KB, image/png)`. In `uv run adk web` you can attach any image with the
paperclip button instead. `ask_with_image.py` shows how an app sends an image in code.

## How it executes
```
 you type:  "Look at receipt.png. Is the printed total correct?"
                    │
                    ▼
     before_model_callback (attach_named_images)
        finds "receipt.png" in the text, reads the file
                    │
                    ▼
     message sent to the model = [ Part(text="Look at receipt.png. Is ..."),  Part(bytes=<png>, type="image/png") ]
                    │
                    ▼
                  LLM reads both parts ──► "No. 3.50 + 2.75 + 4.00 = 10.25, but it says 11.25."

     file not found? the callback adds a text part instead: "[System note: the file menu.png was not found ...]"
```

## Case 1: count what you see
> How many circles, squares and triangles are in shapes.png, and what colour is each kind?

Expect: 3 red circles, 2 blue squares, 1 green triangle. Both Gemini and the local model got it right in testing.
Learn: an image is just another part of the message. The model answers about it like it answers about text.

## Case 2: read text and check it
> Look at receipt.png. Is the printed total correct?

Expect: "No". Both models read the three prices, added them to 10.25, and noticed the printed 11.25 is wrong.
Learn: the model can read text in an image (this is often called OCR) and reason about it, all in one step.

## Case 3: read a chart
> In chart.png, which day had the most visitors, and what is the total for the week?

Expect: Wednesday with 150, and a total of 580. Both models were right in testing and listed all five numbers.
Learn: charts work too, because the numbers are printed on the bars. A chart without labels would force the model to estimate
bar heights, which is much less reliable.

## Case 4: something that is not in the picture
> What is the name of the cashier on receipt.png?

Expect: "There is no cashier name on this receipt." Both models said so in testing.
Learn: the instruction "describe only what you can actually see" works when the model has the image to check against.

## Case 5: a wrong claim about the picture
> chart.png shows that Thursday was the busiest day, right?

Expect: "No", with the real numbers: Wednesday was busiest (150), Thursday was the quietest (80). Both models disagreed with the user.
Learn: a leading question did not push either model into agreeing, because the answer was clearly visible.

## Case 6: an image that does not exist (the most important case)
> What dishes are on menu.png?

There is no `menu.png`. Expect: `[image] menu.png not found in images/`, then "I cannot see menu.png" or similar.
What happened before the fix: the first version of the callback silently skipped the missing file. Gemini then answered "Based on the image
menu.png, here are the dishes listed on the menu" and invented a complete menu, a different one in each of two runs (salads and calamari once,
hummus and falafel the next). The local model said it could not see the image. The fix is one line in `agent.py`: when a file is missing, the
callback adds a text part "[System note: the file menu.png was not found, so no image is attached.]". After that, Gemini said it could not
see the file, in both test runs.
Learn: a model may "answer" about content it never received. When your code fails to provide something, say so in the request. To see the
original behaviour, comment out the `content.parts.append(types.Part(text=...))` line and ask again. Put it back afterwards.

## Case 7: what an image costs, and a model answering without it
    uv run python agent28_multimodal/ask_with_image.py
    MODEL_PROVIDER=local uv run python agent28_multimodal/ask_with_image.py

It asks "Which day had the fewest visitors in this chart?" twice: once as text only, once with `chart.png` attached as a part.
Expect (from testing):
- Gemini: 88 prompt tokens without the image, 1,894 with it. With the image the answer is right (Thursday, 80). Without the image Gemini
  invented a whole week of numbers ("Sunday: approximately 200 visitors ...") and answered "Tuesday".
- Local: 105 and 108 prompt tokens. The local server does not seem to count image tokens in this number, so the cost is not visible here.
  With the image it answered Thursday. Without it, it said "no image was shared".
Learn: an image is far bigger than a short question (about 1,800 tokens here on Gemini), so it costs more and makes the request slower.
And again: a question about "this chart" with no chart attached got a confident made-up answer from Gemini.

## Case 8: images stay in the conversation
In one session, ask about `shapes.png`, then `receipt.png`, then:
> And how many squares were in the first picture?

Expect: "two squares". In testing each later turn showed `[image] attached shapes.png` again, because the callback attaches every image named
earlier in the conversation, on every model call.
Learn: the model can refer back to earlier images because they are sent again each time. That is also why a long conversation with many images
gets expensive: every call carries all of them.

## Case 9: try your own image
Put a PNG or JPG in `agent28_multimodal/images/` (a photo of a shopping list, a timetable, a handwritten note) and ask about it by name.
Learn: try something blurry or handwritten, and see where each model starts to guess. Compare its answer with what is really in the picture.
