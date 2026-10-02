# agent49_distillation: cases, easiest first

Concept: a big model teaches a small one. A large model (here `gemini-2.5-pro`) is slow and costly, but it follows complicated rules well. A small model (the local `qwen3.5-9b`, or `gemini-2.5-flash-lite`) is fast and cheap. "Distillation by labelling" uses the big model ONCE to label a set of examples,
and then lets the small model do the daily work, using those labelled examples. The question is how much of the big model's skill the small one keeps.
Topic: the school-office routing of agent37 (Office, Cafeteria, Transport, Health, Activities, with quirky house rules). Three roles:
- the TEACHER (Pro) is given the written house rules and labels 60 NEW messages (`messages.py`), one time;
- the STUDENTS (local, flash-lite) are NOT given the rules; each gets only the 3 most similar labelled examples (picked with embeddings, as in agent37);
- the TEST is agent37's 24 messages, which none of the models has seen.
Run: `EMBEDDING_PROVIDER=local uv run python agent49_distillation/distill_lab.py` (the embedding model `text-embedding-embeddinggemma-300m` must be loaded in LM Studio; 10 to 15 minutes, because 5 rows x 24 messages x 2 students are asked).
The teacher's labels are saved in `teacher_labels.json`, so you do not need to call Pro again: the lab reads the file. `--refresh` asks the teacher again (about 7 minutes and 47,000 tokens of Pro).
It is a lab, like agents 35-39. The students are called with `common/llm.py`.

## How it executes
```
 ONCE (expensive)                                                         EVERY DAY (cheap)
 60 unlabelled messages                                                   a new message from a parent
        │  + the written house rules                                              │
        ▼                                                                         ▼
  TEACHER  gemini-2.5-pro  ──►  60 labels  ──►  teacher_labels.json        find the 3 most similar labelled examples (embeddings)
        (59 of 60 right)                              │                           │
                                                      └──── examples ─────────────┤
                                                                                  ▼
                                                              STUDENT (small model) sees: 3 examples + the message, NO rules text
                                                                                  │
                                                                                  ▼
                                                                          the department
```

## Case 1: the teacher labels
Run the lab, or read the top of `teacher_labels.json`. Expect (from testing): `TEACHER gemini-2.5-pro: 59/60 of its labels are right (9213 input + 37573 output tokens, 404.7 s, one time only)`. The one mistake:
"Can my son have lactose-free milk with his lunch?", which the teacher sent to Health (the rule "diet-related medical forms go to Health") and the truth is Cafeteria (a menu request, not a medical form).
Learn: the teacher is good, not perfect. And look at the cost: about 780 tokens and 6.7 seconds PER MESSAGE, nearly all of it Pro's hidden thinking.

## Case 2: students with no help
Read the first row. Expect (from testing, 24 test messages): local 18/24, flash-lite 21/24.
Learn: this is the starting point. With only the label names, the students miss the house rules (a trip's bus is Activities, not Transport; lost clothes are Office).

## Case 3: students given the rules in words
Read the second row. Expect: local 23/24, flash-lite 24/24, but the prompt is the longest: 165 and 153 tokens per message (against 70 and 55 for no help).
Learn: when the rules CAN be written down, putting them in the prompt gave the best scores here, and the small models follow them almost as well as the teacher. This is the baseline to beat: do not build a teacher pipeline before trying a good prompt.

## Case 4: students given examples labelled by the teacher
Read the third row. Expect: local 21/24 (up from 18), flash-lite 22/24 (up from 21), at 131 and 117 tokens per message.
Learn: the teacher's knowledge reached the students through the examples alone, without the rules text: three points for the local model, one for flash-lite. That is "distillation by labelling". The students did not reach the rules-in-words score (23 and 24).

## Case 5: do the teacher's mistakes matter?
Read the fourth row: the same 60 messages with the TRUE labels (a human who is never wrong). Expect: exactly the same scores as case 4: 21/24 and 22/24.
Learn: the one wrong teacher label (out of 60) made no difference here (a likely reason, not checked: the mislabelled message was not among the 3 closest examples of any test message). Do not conclude that errors never matter: a teacher that is wrong in 10 of 60, or on one important kind of message, passes those mistakes on to every student, so
check a sample of the teacher's labels by hand.

## Case 6: compare with hand-written examples
Read the last row: agent37's 36 hand-written examples. Expect: local 22/24, flash-lite 24/24, at least as good as the 60 teacher-labelled ones (21 and 22).
Learn: 36 examples written by someone who knows the school did slightly better than 60 labelled by the best model (a likely reason, not checked: their wording and coverage were chosen with the test kinds of message in mind). The advantage of a teacher is quantity (labelling 6,000 messages by hand is work; labelling them with a model is minutes and tokens), not quality.

## Case 7: what it costs (arithmetic, not measured)
The teacher used about 780 tokens per message; the students 117 to 165 (and the local student costs no tokens at all). If the school received 10,000 messages, answering all of them with the teacher would use about 7.8 million tokens, while the one-time labelling (47,000 tokens) plus the students (1.2 to 1.6 million) is
about one fifth of that, and several times faster per message (the local model took about 2 seconds a message in the lab).
Learn: distillation pays when the same task is repeated many times. For a few hundred questions, just use the large model.

## Case 8: when is it worth it?
| | |
|---|---|
| Use a good prompt with rules (case 3) | when the rules can be written down. Best scores here, nothing to build |
| Examples chosen by similarity (agent37) | when the knowledge is easier to show than to say |
| Teacher-labelled examples (this agent) | when you need MANY examples, and the teacher's judgement is better than your small model's |
| Fine-tuning a small model on teacher labels | the next step when examples are not enough (not tried here; check the provider's terms about using model outputs to train another model) |

Learn: the biggest lesson of this lab is the third row of the table: before building any pipeline, measure the plain prompt.

## Case 9: honest limits
Learn: 24 test messages, one run each. A difference of one message (4 percent) is within the noise, so "21 against 22" means nothing by itself; the 3-point gap for the local model between no help and teacher examples is the clearest result. The teacher was given a rule that its labels follow, so its labels are only as
good as that rule. The "small" `gemini-2.5-flash-lite` is itself a capable model.
