# Lab 2 · Build an Action with a contract  (student copy)

**Time:** 30 minutes · **Work in:** pairs · **Badge:** 🏅 Action Engineer
**Primitive practised:** 4 Action (plus design rule 3: *errors teach the model*)

## Why this lab

In Lab 1 the model did the invoice arithmetic itself, and sometimes got it wrong.
Money must be exact every single time, so we move the maths into **deterministic code**
with a **typed contract** (JSON Schema 2020-12). The model only fills in the JSON;
the script does the calculation, and rejects anything that breaks the contract.

## Folder you start with

```
student/
├── invoice-summary-formatter/
│   ├── SKILL.md                    ← Lab 1 reference skill (or paste in your own)
│   └── scripts/
│       ├── totals_schema.json      ← TODO 1: complete the contract
│       └── totals.py               ← TODO 2–4: complete the script
├── inputs/                         ← sample JSON inputs (good and bad)
├── tests/test_totals.py            ← 13 tests: your scoreboard
└── tools/requirements.txt
```

## Setup

```bash
pip install -r tools/requirements.txt
pytest -q          # expect 13 failures right now: that is your starting point
```

## Steps

1. **Contract** (`scripts/totals_schema.json`, TODO 1). Make it reject bad input *by itself*:
   * `lines` and `gst_rate` are required; `lines` has at least 1 item
   * each line item: `qty` > 0, `price` ≥ 0, optional `description`; nothing else allowed
   * `gst_rate` is one of **0, 5, 12, 18, 28** (use `enum`)
   * optional `stated_total` ≥ 0 (the total printed on the invoice)
   * `"additionalProperties": false` at every level
2. **Validate** (already started in `totals.py`): `Draft202012Validator` checks the input.
3. **Compute** (TODO 2) with `Decimal`, never `float`, rounded **half-up** to 2 places:
   subtotal → GST → total. If `stated_total` is given, return the `difference` and
   `status`: `MISMATCH` if more than ₹1.00 off, else `OK`. Print money as strings, e.g. `"1180.00"`.
4. **Errors that teach** (TODO 3 and 4). On any problem print
   `{"error": …, "fix": …, "retryable": true}` and exit with code **2**.
   The `fix` must tell the model exactly what to send instead
   (for example, name the allowed GST rates). Invalid JSON must not crash the script.
5. Run the tests until all pass:
   ```bash
   pytest -q
   echo '{"lines":[{"qty":2,"price":500}],"gst_rate":18}' | python invoice-summary-formatter/scripts/totals.py
   ```
   Expected: `subtotal 1000.00, gst 180.00, total 1180.00`
6. **Update SKILL.md**: replace the "check the arithmetic" step with "build the JSON,
   run `scripts/totals.py`, use its numbers; if it returns an error, follow the `fix`".

## Done when ✅

- [ ] `pytest -q` shows **13 passed**
- [ ] Every bad input returns an actionable `fix` (read them: would *you* know what to do?)
- [ ] No stack trace ever reaches the output
- [ ] SKILL.md tells the model to call the script instead of doing maths

## Hints

* `Decimal(str(0.1))` is exact; `Decimal(0.1)` is not.
* `ROUND_HALF_UP`: 0.625 → 0.63. Python's `round()` would give 0.62.
* Each jsonschema error has `.validator` (`"required"`, `"enum"`, `"minItems"`,
  `"additionalProperties"`, `"exclusiveMinimum"`, `"type"`…). Use it to pick the right fix text.
* Let the **schema** reject `gst_rate: 18.5`. Don't write an `if` for it.

## Stretch

Wrap the same function as an **MCP tool** (`pip install mcp`) so any MCP-capable agent
can discover its schema. Ask your trainer for the reference `mcp_server.py` afterwards.

## Think about it

1. Why is `"retryable"` useful? When should it be `false`?
2. Which is safer: the model doing maths, or the model filling a JSON form? Why?
