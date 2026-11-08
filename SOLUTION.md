# Solution — Exercise 03

## What's on this branch

- **`ANSWER-KEY.md`**: the correct extraction for each email, the trap in it, and which other answers are defensible. Use it for step 5.
- **`runs/`**: my raw outputs, exactly as saved. `runs/chat/` is the chat step, and `runs/opus-5-5/` and `runs/haiku-5-5/` are the API runs, each with `prompt/` and `schema/`. Run `python -m src.main check runs/opus-5-5/prompt` (or any of the others) to get my tables back.

## What I found

All runs were on 8 November 2026, three runs per email.

| | parses | right shape | adds up | traps handled |
|---|---:|---:|---:|---:|
| Chat, code-block copy icon | 9/9 | 9/9 | 9/9 | all |
| Chat, message copy button, no "Return only the JSON." | 0/1 | – | – | – |
| API, Opus 5.5, prompt only | 0/18 | – | – | 18/18 inside the fence |
| API, Opus 5.5, schema | 18/18 | 18/18 | 18/18 | 18/18 |
| API, Haiku 5.5, prompt only | 3/18 | 3/18 | 3/18 | 18/18 inside the fence |
| API, Haiku 5.5, schema | 18/18 | 18/18 | 18/18 | 18/18 |

**The chat looked perfect because I was the repair step.** I copied the replies with the small icon on the code block, and that icon copies what's inside the fence, not the fence itself. When I used the copy button under the whole message instead, and dropped "Return only the JSON.", the reply came back in a ```` ```json ```` fence with a paragraph after it explaining the refund. Nothing in the chat window tells you that's what a program would receive.

**Asking nicely almost never worked, and always failed the same way.** Through the API, all 18 Opus prompt-only replies were wrapped in a code fence, with no text before or after it and correct JSON inside. Haiku fenced 15 and returned 3 as bare JSON, so 3 of 18 parsed.

Haiku is the more dangerous result. A model that fences every time, you notice on the first run. A model that sometimes returns clean JSON lets you build on it, and then breaks in production. In both cases it's tempting to strip the fence with a regex and move on. That's a parser for one habit, and it breaks on the first reply with a sentence after the fence.

**The schema fixed parsing completely, on both models.** 36 of 36 parsed, had the right shape, and added up.

**Neither model fell for a single trap.** VAT already included, the forwarded correction, the American date, the quote marks and backslash, the refund with no order number: every run got every one right, in both modes. The schema has nothing to do with that. Strip the fence from the prompt-only replies and the values inside are just as correct. A schema controls the shape of the answer, not the reading behind it. So my "adds up" check never fired. It will on your own documents, and even then it only catches answers that contradict themselves. Most of the traps, had a model fallen for them, would have produced an answer that adds up and is still wrong. See `ANSWER-KEY.md`.

**What varied were the rules I thought I'd stated.** All of it was on one email, `05-trailhead`:

| | socks `unit_price` | `order_id` |
|---|---|---|
| Opus, prompt only | null, null, null | `TH-88214` x3 |
| Opus, schema | 19.00, 19.00, 19.00 | `TH-88214` x3 |
| Haiku, prompt only | null, null, 19.00 | `TH-88214` x3 |
| Haiku, schema | 19.00, 19.00, null | `#TH-88214`, `TH-88214`, `TH-88214` |
| Chat, fresh / same chat | 19.00 / null | `TH-88214` |

The email prints "Merino socks (3-pack) x2 .... $38.00" and no unit price. Both the prompt and the schema say `unit_price` is "the price of one unit, or null if the email doesn't state it". Opus followed that in every prompt-mode run and broke it in every schema-mode run. My guess is that a rule in a field description carries less weight than the same rule in the prompt. Three runs is a signal, not proof.

The order number is the other one. "The order number as written" is ambiguous when the email writes `#TH-88214`. Is the `#` part of the number? One Haiku run said yes. A downstream system would treat those as two different orders.

The schema fixed the shape. The rules were still my job. Both of these belong in `src/validate.py`, not in a sharper prompt: strip a leading `#` from order IDs, and decide once whether a missing unit price is computed or null, then enforce it.

## The numbers

| Opus 5.5 | tokens in | tokens out |
|---|---:|---:|
| prompt only, 18 calls | 10,356 | 7,530 |
| schema, 18 calls | 25,584 | 3,827 |

Schema mode reads about 2.5 times the input, because the schema is added to what the model sees. Prompt mode wrote about twice the output, even though its replies are no longer. The difference is most likely thinking, which `response_text` skips and the run doesn't save.
