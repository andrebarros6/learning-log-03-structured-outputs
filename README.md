# Learning Log — Exercise 03: Structured outputs

**Issue 3 of 30 · Working with the models** · [Read the issue](https://barrosbuilds.com/log) · [All exercises](https://github.com/andrebarros6/learning-log)

**Kind:** script, chat first · **Needs:** a Claude account (the free plan works), Python 3.10+, git, an Anthropic API key (separate from a Claude subscription) · **Cost:** the chat part is free; the API part is about $0.40 on Claude Opus 5.5 with the default three runs (checked 3 November 2026)

Get JSON that parses every time, without scraping it out of the reply.

---

## The theory

Asking for JSON is a request, not a contract. "Return only the JSON" works often enough that you build on it, and then a reply arrives wrapped in a code fence, or with a friendly sentence in front, or with a product name whose quote mark isn't escaped. Your code breaks on output that looks fine to you.

The usual response is to repair it: strip the fences, find the first `{` and the last `}`, regex out the part you want. Every repair works until the response changes shape in a way you didn't anticipate, and then it breaks quietly, on a format you've never seen.

There are three levels, and the shift that matters is from the first to the second:

1. **Shape in the prompt.** You describe the fields and ask nicely. Nothing enforces it. This is *hoping* the shape holds.
2. **Shape in a schema.** You hand the API a JSON Schema, and generation is constrained to it. The reply parses, has every required field, and has the types you declared. This is *constraining* it.
3. **Validation after.** A schema guarantees shape, not truth. A perfectly shaped order whose items don't add up to its total parses every time and is still wrong. So you check the values too.

The chat window only gives you the first. The API gives you the second, which is why this exercise starts in the chat and ends in a script.

## What you'll do

1. **In the chat:** extract six messy order emails with a prompt that asks for JSON, and save each reply exactly as it came.
2. **Check what the chat gave you:** a script runs `json.loads` on each reply as it stands, with no repairs, then checks the shape and the sums.
3. **Through the API, prompt only:** the same prompt, three runs per email. Same question: does it parse as it comes?
4. **Through the API, with a schema:** the same emails, with the field list moved out of the prompt and into `output_config.format`. Count the failures.
5. **Read the values:** open the outputs that parse and check them against the emails. Each email has one trap in it. The schema can't catch any of them.

## When this is not the right tool

If you want prose, don't force JSON. Constraining the shape of a generative task, such as a summary, an explanation or a draft, costs quality. The model spends its effort fitting the format instead of writing well. Use a schema when a program reads the output. When a person reads it, leave it as text.

---

## Setup

```bash
git clone https://github.com/andrebarros6/learning-log-03-structured-outputs
cd learning-log-03-structured-outputs
python -m venv .venv
```

Activate it. The command depends on your shell:

```bash
source .venv/bin/activate        # macOS / Linux
```

```powershell
.venv\Scripts\Activate.ps1       # Windows PowerShell, including the VS Code terminal
```

If PowerShell says running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again. Then:

```bash
pip install -r requirements.txt
```

For steps 3 and 4 you need an API key from [the Claude Console](https://platform.claude.com). It is not the same thing as a Claude Pro or Max subscription. Put it in a `.env` file (gitignored):

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run it

### 1. In the chat

Open [claude.ai](https://claude.ai). For each email in [`data/emails/`](data/emails/):

1. **Open a fresh chat.**
2. Paste the prompt from [`prompts/prompt-only.md`](prompts/prompt-only.md), then the email underneath it, as one message.
3. Copy the reply with the copy button, and paste it into `chat/01.txt`, `chat/02.txt` and so on. Don't tidy it. What the copy button gives you is what a program would get.

Then, before the next step, **break it on purpose**. Pick one email and try at least one of these:

- Ask the same thing twice, in two fresh chats. Are the two replies the same shape?
- In the same chat, ask "now do the same for this one" and paste a second email. Do the field names hold?
- Drop "Return only the JSON." from the prompt.

Save those replies in `chat/` too, named so you remember which was which.

### 2. Check what the chat gave you

```bash
python -m src.main check chat
```

No API key needed. For each reply it says whether it parses as it stands, whether it's the right shape, whether its numbers add up, and if not, why not.

### 3 and 4. Through the API

```bash
python -m src.main run --mode prompt
python -m src.main run --mode schema
```

Each one sends all six emails three times and prints the same table. Every raw response is saved under `out/prompt/` or `out/schema/`, so you can open the ones that failed.

Read [`src/extract.py`](src/extract.py) while it runs. The two modes differ in exactly one place: where the field list lives. In prompt mode it's in the prompt. In schema mode it's in the request, generated from the `Order` model in [`src/schema.py`](src/schema.py), and the prompt shrinks to one line ([`prompts/schema.md`](prompts/schema.md)).

### 5. Read the values

"Adds up" checks that the extraction agrees with itself. It doesn't know what the email said. For each email, open one schema-mode output next to the email and check the values by hand: the date, the total, the tax, whether every item belongs there. There's a trap in each one: a total with VAT already in it, a correction that replaces an earlier order, a date written the American way, a product name with a quote mark in it, a refund with no order number.

## Checking your work

```bash
pytest
```

The tests need no API key. They cover the checker, the sums, the request each mode sends, and that the schema stays inside what the API supports. If you change `Order`, run them again. The schema test will tell you if you've used something structured outputs doesn't accept.

## The solution

```bash
git checkout solution
```

`SOLUTION.md` has my run: what the chat gave me, what each mode scored over all the runs, and which traps the model fell into. `ANSWER-KEY.md` has the correct extraction for every email, so you can check step 5 properly.

## Bring your own documents

The order emails are scaffolding. **The exercise is a document type you actually process**: invoices, booking confirmations, bank notifications, CVs, whatever you currently read and retype.

Do it after the solution, because your own documents have no answer key:

1. Put five real examples in a `mine/` folder. It's gitignored. Don't commit real receipts or personal documents to a public repo.
2. Write the schema first: the fields you'd actually use, with a description on each one saying what goes there when the document is ambiguous.
3. Write the checks a schema can't make: totals that must add up, dates that can't be in the future, whatever "self-consistent" means for your documents.

## A note on the numbers

The cost line at the top was measured on 3 November 2026, on Claude Opus 5.5. Prices change. Pass `--model` to try another model; the cheaper ones are a good test of whether the schema is doing the work or the model is.

Schema mode sends more input tokens than prompt mode, even though its prompt is shorter, because the schema is added to what the model reads. Check the token line at the end of each run.

---

## Questions, corrections, things that broke

[Discussions on the hub repo](https://github.com/andrebarros6/learning-log/discussions) are one place for all exercises.

Found a step that's gone stale because a tool changed? Open an issue here. Corrections are genuinely welcome; things breaking in public is the format.

## Licence

MIT. See [LICENSE](LICENSE). The exercise is yours to keep.
