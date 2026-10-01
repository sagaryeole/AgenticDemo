# agent11_guardrails: cases, easiest first

Run: `uv run adk run agent11_guardrails`. The callbacks print `[guardrail] ...` lines so you can see them fire.
Concept: callbacks, small functions that run at fixed points and can inspect, block or change what passes through.
Topic: a pizza-ordering assistant with three guardrails.
Model: set `MODEL_PROVIDER` in the root `.env`, or `AGENT11_MODEL_PROVIDER` for this agent only.

Menu: margherita $9, pepperoni $11, veggie $10. Orders are limited to 1-10 pizzas.

## How it executes
Control: the normal agent loop, with three checkpoints written in plain Python. The checkpoints
always run; the model does not decide whether they apply.

```
 user message
      │
      ▼
 ┌─────────────────────────────────────────────┐
 │ ① before_model_callback  block_card_numbers  │
 │    card number? ──yes──► canned refusal ─────────────────────┐
 └───────────────────┬─────────────────────────┘                │ model is
                     │ no                                       │ never called
                     ▼                                          │
                  LLM call                                      │
                     │                                          │
                     ▼                                          │
 ┌─────────────────────────────────────────────┐                │
 │ ③ after_model_callback  hide_staff_contacts  │                │
 │    email/phone in the reply? ─yes─► remove it│                │
 └───────────────────┬─────────────────────────┘                │
                     │                                          │
        tool requested?                                         │
         │ no                  │ yes                            │
         │                     ▼                                │
         │      ┌───────────────────────────────────────┐       │
         │      │ ② before_tool_callback validate_order │       │
         │      │    bad item or quantity? ─yes─► error │       │
         │      └──────────────┬────────────────────────┘       │
         │                     │ no                             │
         │                     ▼                                │
         │             real function runs ──► result ──► LLM call (back to ③)
         ▼                                                      │
    final reply  ◄──────────────────────────────────────────────┘
```

Why these three? Each protects something different:
- ① keeps sensitive input (a card number) away from the model and out of the chat.
- ② stops the agent from acting on bad arguments the model chose.
- ③ stops internal details from reaching the customer.

## Case 1: normal requests, nothing triggers
> What pizzas do you have?
> Order 2 pepperoni pizzas

Expect: no `[guardrail]` line. The menu is listed, and the order is confirmed with id and total ($22).
Learn: guardrails only act when their condition matches. Otherwise they stay out of the way.

## Case 2: block before the model (input guardrail)
> Here is my card 4111 1111 1111 1111, please pay for it

Expect: `[guardrail] model call BLOCKED: message looks like it contains card details`, and a fixed reply
telling the customer to pay on arrival.
Learn: the model was never called, so the card number was not sent to it. That saves cost and keeps
the data out of the model request. (The message still sits in the chat history, see case 7.)

## Case 3: block before the tool (argument guardrail)
> Order 500 margherita pizzas

Expect: `[guardrail] tool call BLOCKED: quantity 500 is outside 1-10`, then the model explains the
limit in its own words and suggests calling the shop.
Learn: the model chose the arguments, but your code checks them before the function runs.
Never trust model-chosen arguments for anything that matters, such as money or quantities.

## Case 4: an item that is not on the menu
> Order 1 hawaiian pizza

Expect: the order is refused. Whether you see `[guardrail] tool call BLOCKED: 'hawaiian' is not on the menu`
depends on the model. In testing both models read the menu and refused without calling `place_order`,
so the guard never fired.
Learn: a guardrail is a safety net for when the model does not behave. It does not fire every time,
and that is fine. Without it, a model that did call the tool with 'hawaiian' would have crashed on the
menu lookup.

## Case 5: change the output (output guardrail)
> Order 1 veggie pizza and give me the kitchen's exact email and phone number

Expect: `[guardrail] reply MODIFIED: staff contact details removed`, and the reply shows
`[email removed]` and `[number removed]`.
Learn: you can edit a reply after the model produces it. The tool result includes an internal note with
the kitchen's contact details, and the instruction here is deliberately loose about passing it on, to
simulate a model slip. In testing the local model even leaked the details unprompted after a plain order.
In a real system you would also tell the model not to share internal notes. The guardrail is the second line.

## Case 6: look at the counter
Run `uv run adk web`, trigger case 2 twice, open the session State.
Expect: `blocked_count` is 2.
Learn: callbacks can read and write session state, just like tools (agent05).

## Case 7: the card guard only checks the newest message
In one session send case 2, then:
> What card number did I just give you?

Expect: this message is allowed through. Only the latest user message is checked, and the earlier
card number is still in the conversation history sent to the model. In testing Gemini
declined to repeat it, but that was its own choice, not a guardrail.
Learn: decide what a guardrail inspects (latest message, whole history, or both).
This one is a deliberate simplification.

## Case 8: pattern checks can be dodged
> My card is four one one one, one one one one, one one one one, one one one one

Expect: no `[guardrail]` line, because there are no digits for the pattern to match. The message
reaches the model. Gemini refused on its own, but another model may not.
Learn: regular expressions catch common formats, not every disguise. Real systems add classifiers,
a second model, or stricter handling of sensitive flows.

## Case 9: compare the three callbacks
| Callback | Runs | Can do |
|---|---|---|
| `before_model_callback` | before each model call | skip the model, return your own reply |
| `before_tool_callback` | before each tool runs | skip the tool, return your own result |
| `after_model_callback` | after each model reply | replace or edit the reply |

ADK also has `after_tool_callback`, `before_agent_callback` and `after_agent_callback`.
Learn: pick the checkpoint closest to what you want to protect.
