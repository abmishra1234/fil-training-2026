# CabRoster — Instructor Pack (do not share with students)

Contains the reference solution, both test suites and the tools used to check the suites.

```
app/                    reference solution (passes 100% of both suites)
tests/conftest.py       harness: in-memory DB + fake clock per test
tests/support.py        Api helper, calendar constants, JWT helpers
tests/simple/           38 basic tests  (also shipped in the student starter kit)
tests/full/             392 cases (+5 stretch) — the grading suite
mutate.py               injects 48 bugs one at a time and reports which the suite catches
build_catalogue.py      regenerates the Excel test catalogue from test docstrings
```

## Run

```bash
pip install -r requirements.txt
pytest tests/simple                          # 38 passed
pytest tests/full -m "not stretch"           # 392 passed
pytest -m stretch                            # 5 passed (reports)
BCRYPT_ROUNDS=4 pytest                       # same, ~40 s instead of minutes
```

## Grading a student submission

1. Copy `tests/full` into the student's project next to their `tests/simple`. `conftest.py` and `support.py` are identical in both packs.
2. `pytest tests/full -m "not stretch" -q --tb=no -rN | tail -1` gives the pass count.
3. Score = passed / 392. Stretch tests are bonus.
4. Useful for feedback: `pytest tests/full -q --tb=line` lists each failing rule with the test ID in its docstring (F-BKG-06 etc.). The Excel catalogue explains each ID.

## Suite strength (mutation testing)

| Suite | Injected bugs caught |
|---|---|
| Simple | 5 / 48. It checks wiring, not rules, so passing it proves very little |
| Full | **46 / 48**. The 2 survivors are equivalent mutants: code paths that can never run, because cancelling a booking already sets `trip_id = NULL` |

## Speed note

Student code usually uses bcrypt with 12 rounds, so the full suite takes about 6 minutes (measured: 5 min 39 s for the reference).
The admin password hash is cached once per session to save time.
