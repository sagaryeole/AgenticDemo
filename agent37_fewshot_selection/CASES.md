# agent37_fewshot_selection: cases, easiest first

Concept: few-shot prompting means showing the model solved examples inside the prompt. It is the cheapest way to teach a model a rule that
is not written anywhere else. The question here is WHICH examples to show. Instead of the same ones every time, find the ones most similar
to the new message with embeddings (labs 17-18) and show those.
Topic: routing messages from parents to a school department (Office, Cafeteria, Transport, Health, Activities). The school has house rules that no
stranger could guess, for example: lunch money goes to Cafeteria, but a food-allergy form goes to Health; the bus for a school TRIP goes to
Activities, not Transport. The rules live only in the 36 labelled examples in `examples.py`.
Two files:
- `fewshot_lab.py` compares four ways to build the prompt on 24 new messages:
  `uv run python agent37_fewshot_selection/fewshot_lab.py` (add `MODEL_PROVIDER=local EMBEDDING_PROVIDER=local` for the local model; it takes a few minutes).
- `agent.py` is the agent, which picks the examples for every message: `uv run adk run agent37_fewshot_selection`.
Embeddings follow the chat provider unless `EMBEDDING_PROVIDER` is set. The agent prints `[examples] for '<message>': [labels]`, the labels of the
examples it chose, so you can see what the model was shown.

## How it executes
```
 parent: "Is the bus for the camping weekend free?"
        │
        ▼
 instruction function build_instruction(ctx)     runs before EVERY model call (same mechanism as agent29)
   1. embed the message                                   ──┐
   2. cosine against the 36 stored examples               ──┤  labs 17-18
   3. keep the 3 closest:                                   │
        "bus for the trip to the zoo ..."     -> Activities │  ◄── written into the instruction
        "coach to the swimming gala ..."      -> Activities │
        "what time does bus 12 leave ..."     -> Transport  │
        ▼
      LLM sees: rules in words + these 3 examples + the message ──► "Activities - the bus is for a school trip"
```

## Case 1: no examples (zero-shot)
Run the lab and read the `zero-shot` line. Expect (from testing, 24 messages): Gemini 21 right, local 18.
Learn: a good model guesses most routes from the label names alone. Its mistakes are exactly the house rules: "the coach to the museum" and "the bus for the camping weekend" went to
Transport on both models, "the lost scarf" went to Activities on the local model.

## Case 2: the same examples every time (fixed)
Read the `fixed` line. Expect: Gemini 23, local 20.
Learn: three examples help a little even when they are the same for every message, because they show the answer format and a few house rules. But they cannot cover all the rules: the museum coach
was still wrong on both models, the doctor's note for sports day and the egg allergy on the local model.

## Case 3: random examples
Read the `random` line. Expect: Gemini 22, local 16.
Learn: this is the control. On the local model, random examples were worse than none at all (16 against 18): examples are evidence the model weighs, and unrelated evidence can mislead it.
On Gemini they made little difference (22 against 21).

## Case 4: the most similar examples (selected)
Read the `selected` line. Expect: Gemini 23, local 22 (out of 24): the best result on the local model, level with `fixed` on Gemini.
Learn: similar examples carry the matching house rule: the museum coach and the camping bus find the "bus for the zoo trip" example, and the rule travels with it. The gain is clear on the local model
(22 against 18 for no examples and 20 for fixed ones) and small on Gemini, which was already good (23 against 21 and 23). This is retrieval (agent19) used for a different purpose: not to find an answer,
but to find the evidence about how to behave.

## Case 5: a wrong choice of examples shows up in the prompt
    uv run adk run agent37_fewshot_selection
> Is the bus for the camping weekend free?

Expect (from testing): Gemini's embeddings chose `['Activities', 'Activities', 'Activities']` and it answered "Activities". The local embedding model
chose `['Transport', 'Activities', 'Activities']` and the local chat model answered "Transport", wrong.
Learn: the quality of the examples depends on the embedding model, and the agent printed what it chose, so the cause is visible. When a few-shot
agent goes wrong, read the chosen examples first.

## Case 6: another message
> She dropped her lunch card on the way. Can it be blocked?
> Where do I find my son's lost scarf?

Expect (from testing, in the agent): the scarf finds three Office examples and is routed to Office on both models. For the lunch card both models were shown two
Cafeteria examples and one Office example; the local model answered "Cafeteria" (right), Gemini answered "Office" (wrong). In the lab, `selected` missed the museum coach on Gemini
(it went to Transport), and the camping bus and the lunch card on the local model.
Learn: even the best examples are advice, not a guarantee.

## Case 7: how many examples, and the cost
Change `K = 3` in `fewshot_lab.py` to 1, then to 8, and run again.
Expect: not measured here. Think about it first: more examples add more evidence, but also more tokens in every call, and weaker examples at the
end of the list.
Learn: the number of examples is a setting to tune on your own test set, like top-k in agent19.

## Case 8: honest limits, and a lesson about noise
Learn: 24 messages, one run each at temperature 0. A difference of one or two messages is within the noise, and Gemini's four results (21, 23, 22, 23) are that close.
A first version of this lab sent no instruction line at all, and the local `fixed` result was 16 instead of 20, while Gemini's selected was 23 either way. That small change to the prompt moved one
row by four messages. Do not read much into a single number. What held up in both runs on the local model: selected examples were the best and unrelated examples did not help. Selection also costs
an embedding call per message and needs a pool of good labelled examples. Read the mistakes the lab prints, because they tell you which examples to add to the pool.
