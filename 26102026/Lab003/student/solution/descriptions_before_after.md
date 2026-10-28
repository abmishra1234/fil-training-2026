# Descriptions before and after (reference)

Scores are from `trigger_eval.py` with `LLM_MODE=mock` on `evals/triggers.jsonl` (10 prompts).
Real-model scores vary; re-run with `--runs 3`.

## 1. Weak (ships in the student folder) → 5/10
> Helps with invoices and finance stuff.

No *Use when*, no *Do not use for*. All 5 positives missed.

## 2. Lab 1 reference → 8/10
> Use when the user shares a vendor invoice (pasted text or a file) and asks to summarise,
> check or format it into the FIL AP invoice summary. Do not use for creating purchase
> orders, scheduling or making payments, answering general GST questions, or filing tax returns.

Misses "bill" and "supplier" wording; users don't always say "vendor invoice".

## 3. Tuned → 9/10 (mock), typically 10/10 with a real model
> Use when the user shares a vendor or supplier invoice or bill they received and asks to
> summarise, check, review or format it into the FIL AP invoice summary, or to check whether
> its totals add up. Do not use for creating or raising invoices to bill our own customers,
> purchase orders, scheduling or making payments, general GST rate questions, or filing GST returns.

What changed and why:
* **bill, supplier, review, totals add up** → fixed the missed triggers (users' real words)
* **they received** + **invoices to bill our own customers** → names the direction, the
  key near-miss
* still one sentence each for *Use when* and *Do not use for*: short enough to sit in every
  agent's context
