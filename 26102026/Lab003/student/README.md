# Lab 3 · Trigger evals: does it load at the right time?  (student copy)

**Time:** 25 minutes · **Work in:** pairs · **Badge:** 🏅 Trigger Tuner
**Primitives practised:** 2 Trigger, 8 Evals (design rule 2: *two failure surfaces*)

## Why this lab

A perfect skill is useless if it never loads, and harmful if it loads for the wrong
request. Before loading anything, an agent sees only each skill's **name + description**.
In this lab the model plays that router, and you measure how often it picks your skill
at the right time.

## Folder you start with

```
student/
├── skills/
│   ├── invoice-summary-formatter/SKILL.md   ← YOUR skill (starts with a weak description)
│   ├── purchase-order-creator/SKILL.md      ← decoy (do not edit)
│   ├── payment-scheduler/SKILL.md           ← decoy (do not edit)
│   └── gst-faq-answerer/SKILL.md            ← decoy (do not edit)
├── evals/triggers_template.jsonl            ← 3 example prompts; you add 7 more
└── tools/trigger_eval.py
```

## Setup

Same `.env` as Lab 1 (copy it into this lab folder, or `cp tools/.env.example .env`), then
`python tools/check_setup.py`. `LLM_MODE=mock` gives an offline, word-overlap router for practice.

## Steps

1. Copy `evals/triggers_template.jsonl` to `evals/triggers.jsonl`. Add **7 more lines**
   so you have **10 prompts**:
   * **5 positives**: requests that SHOULD load `invoice-summary-formatter`.
     Vary the words: *bill*, *supplier*, *check the totals*, *review before approval*…
   * **5 near-misses**: requests that sound similar but should NOT load it. Set
     `expected` to the decoy that should win, or `NONE`.
     Ideas: raising a PO, scheduling a payment, a GST rate question, filing a return,
     **creating an invoice for our own customer**.
2. **Baseline.** Run with the weak description that ships in the folder:
   ```bash
   python tools/trigger_eval.py --skills skills --evals evals/triggers.jsonl \
          --target invoice-summary-formatter
   ```
   Note the score, missed triggers and false triggers.
3. Paste your **Lab 1 description** into `skills/invoice-summary-formatter/SKILL.md`. Run again.
4. **Tune.** Read every `XX` line:
   * *missed trigger* → add the user's words to **Use when…**
   * *false trigger* → add the near-miss to **Do not use for…**
   Re-run until you get **at least 9/10**. Use `--runs 3` for the final run:
   LLM routing is not perfectly repeatable.
5. Post your **before → after** score on the class board.

## Done when ✅

- [ ] `triggers.jsonl` has 5 positives + 5 near-misses
- [ ] Final score ≥ 9/10 (≥ 27/30 with `--runs 3`)
- [ ] You can explain which words fixed the false triggers
- [ ] Before/after score is on the class board

## Hints

* Write prompts the way colleagues really type, not the way the description is written.
  Copying the description's words into the prompts makes a test that always passes.
* "Invoice" appears in invoices we **receive** and invoices we **send**. Which one is yours?
* Don't touch the decoys. In real life you don't control other teams' skills.

## Think about it

1. Why test near-misses at all? What would 10 positives alone tell you?
2. Your description is now longer. Is there a cost? (Hint: it is in context for every request.)
