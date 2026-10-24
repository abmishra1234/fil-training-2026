# Lab 1 · Write your first SKILL.md  (student copy)

**Time:** 25 minutes · **Work in:** pairs · **Badge:** 🏅 Instruction Author
**Primitives practised:** 1 Instruction, 2 Trigger

## The situation

The FIL Accounts Payable (AP) team receives hundreds of vendor invoices a week.
They want an AI agent skill that turns any invoice into the same one-screen summary,
so a reviewer can approve it in under a minute. You will write that skill.

## What the AP team needs (your requirements)

Your skill's output **must** contain:

1. A markdown table with these rows: `Vendor`, `GSTIN`, `Invoice No`, `Invoice Date`,
   `Line items`, `Subtotal`, `GST`, `Grand total`
2. Amounts as printed on the invoice, written like `INR 14,750.00`
3. One line `Status: OK`, `Status: MISMATCH` or `Status: NEEDS_INFO`
4. One line `Notes: …` explaining anything the reviewer must know

Business rules the AP team gave you:

* No GSTIN on the invoice → the invoice cannot be processed → `NEEDS_INFO`
* Line amounts don't add up, or subtotal + GST ≠ grand total (more than ₹1 off) → `MISMATCH`
* Never "fix" the vendor's numbers. Report problems, don't hide them.

## Folder you start with

```
student/
├── invoice-summary-formatter/SKILL.md   ← the skeleton you complete
├── samples/                             ← 3 real-looking invoices + cases.jsonl
└── tools/                               ← checker and runner (do not edit)
```

## Setup (2 minutes)

```bash
pip install -r tools/requirements.txt
cp tools/.env.example .env        # Windows: copy tools\.env.example .env
# In .env set ONE line:  LLM_MODE=enterprise  (in FIL, fill the FIL_* block with your team's credentials)
#                    or  LLM_MODE=direct      (at home, fill OPENAI_API_KEY)
python tools/check_setup.py      # must end with "All good"
```
No credentials yet? `LLM_MODE=mock` runs the tools offline (the mock will not write real
answers). Details and troubleshooting: `SETUP_DIRECT_VS_ENTERPRISE.md`.

## Steps

1. Open `invoice-summary-formatter/SKILL.md`. Keep the folder name; it must match `name:`.
2. **Trigger.** Write the `description`: one sentence starting `Use when…` (the requests
   this skill should handle, in words users actually type) and one `Do not use for…`
   (near-misses: purchase orders, payments, GST questions…).
3. **Instruction.** Fill in all five sections:
   * **Role** – who the agent is acting as
   * **Procedure** – numbered steps, one action per step
   * **Decision rules** – if-then rules for NEEDS_INFO and MISMATCH
   * **Output contract** – the exact table and the two lines, nothing else
   * **Examples** – two short input → output pairs (make up small invoices)
4. Lint it:
   ```bash
   python tools/check_skill.py invoice-summary-formatter
   ```
   Fix every `FAIL` until you see `RESULT: PASS`.
5. Run it on the three sample invoices:
   ```bash
   python tools/run_cases.py invoice-summary-formatter samples/cases.jsonl
   ```
   Read the outputs in `outputs/`. If a case fails, improve your **instruction**
   (not the test!) and run again.
6. Swap SKILL.md files with the pair next to you. Can they follow yours without asking?

## Done when ✅

- [ ] `check_skill.py` prints `RESULT: PASS`
- [ ] All 5 instruction sections are present and specific
- [ ] `run_cases.py` shows **3/3** cases matching the contract
- [ ] A neighbour pair can follow your SKILL.md without asking you

## Hints

* "Be accurate and helpful" is not a rule you can test. "If GSTIN is missing, set Status
  to NEEDS_INFO" is.
* Say what happens when two rules apply at once (which one wins?).
* Tell the model to output **only** the table and the two lines.
* Stuck on the description? Ask: *what would a colleague type in chat?*

## Think about it (for the debrief)

1. Invoice 3 is wrong by exactly ₹1,000. Did the model catch it every time? What does that
   tell you about doing arithmetic inside a prompt? (Lab 2 answers this.)
2. Which section of your SKILL.md did you rewrite most? Why?
