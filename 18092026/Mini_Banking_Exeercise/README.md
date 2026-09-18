# Mini Banking & Payments System — starter repo

Python OOP + Exception Handling coding test. **90 minutes.**

Read `EXERCISE.md` (or the PDF handout) first — it is the full specification.
This file only tells you how to run things.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.10 or newer.

## Run the tests

```bash
python -m pytest                       # everything
python -m pytest tests/test_money.py   # one task at a time -- do this
python -m pytest -x -q                 # stop at the first failure
python -m pytest -k overdraft          # one behaviour
```

### Windows / Git Bash troubleshooting

Prefer `python -m pytest` over plain `pytest`. It guarantees that pytest runs
with the same Python interpreter as the active virtual environment. On some
Windows machines, especially those with Anaconda installed, the `pytest`
command can still resolve to Anaconda even when the prompt displays `(.venv)`.
That mismatch may produce `ModuleNotFoundError: No module named 'minibank'`.

In Git Bash, activate and verify the environment with:

```bash
source .venv/Scripts/activate
python -c "import sys; print(sys.executable)"
python -m pytest
```

The printed interpreter should be the `.venv/Scripts/python.exe` inside this
project. If the shell previously cached another executable, run `hash -r`
after activating the environment.

On a fresh clone you should see **171 tests**, of which 14 already pass
(they cover `exceptions.py` and `TransactionType`, which are given to you).
Your job is the other 157.

## Suggested order

Each module depends only on the ones above it, so work top to bottom and keep
the suite green as you go.

| # | File | Tests | Budget |
|---|------|-------|--------|
| 1 | `minibank/money.py` | `tests/test_money.py` | 20 min |
| 2 | `minibank/transaction.py` | `tests/test_transaction.py` | 10 min |
| 3 | `minibank/mixins.py` | `tests/test_mixins.py` | 10 min |
| 4 | `minibank/accounts.py` | `tests/test_accounts.py` | 25 min |
| 5 | `minibank/strategies.py` | `tests/test_strategies.py` | 10 min |
| 6 | `minibank/bank.py` | `tests/test_bank.py` | 15 min |

## Smoke test

```bash
python demo.py
```

Not graded, but if it runs end to end your wiring is almost certainly right.

## Rules

* **Standard library only.** `decimal`, `abc`, `enum`, `dataclasses`,
  `functools`, `itertools`, `json`, `re`, `datetime` are all you need.
* **Do not edit `tests/`.** Do not rename anything in `minibank/`.
  Adding private helpers inside the given modules is encouraged.
* `minibank/exceptions.py` and `TransactionType` are complete — use them.
* Never use `float` for money. Never write a bare `except:`.

## What to submit

The repo, plus a short `NOTES.md` covering:

1. One design decision you made and the alternative you rejected.
2. Where you used composition instead of inheritance, and why.
3. Anything left unfinished, and what you would do next.
