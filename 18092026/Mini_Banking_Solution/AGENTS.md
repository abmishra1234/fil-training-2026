# Mini Banking Exercise: Testing Guide

This directory is an intentionally incomplete Python training exercise. The
`NotImplementedError` placeholders in `minibank/` are part of the starter
state; do not implement them unless the user explicitly asks for a solution.

## Environment

- Python 3.10 or newer is required.
- Use the existing virtual environment on Windows when available:
  `.venv\Scripts\python.exe`.
- Install dependencies with `python -m pip install -r requirements.txt` only
  when the environment has not already been prepared.

## Clean compile

Remove generated `.pytest_cache` and `__pycache__` directories, then run:

```powershell
.\.venv\Scripts\python.exe -m compileall -f minibank demo.py
```

A successful clean compile means every source file is syntactically valid. It
does not mean the exercise implementation is complete.

## Tests

Run the complete suite without creating a pytest cache:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

Run one exercise section while developing:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_money.py -p no:cacheprovider
```

The untouched starter repository contains 171 tests. Only the tests covering
the supplied exception hierarchy and `TransactionType` pass; most tests are
expected to fail until the exercise is implemented. The completed exercise is
done only when all 171 tests pass and `python demo.py` succeeds.

## Change boundaries

- Do not edit files under `tests/`.
- Do not rename modules, classes, methods, or parameters in `minibank/`.
- Use only the Python standard library in the implementation.
- Never use binary floating-point arithmetic for monetary calculations.
- Preserve immutable/read-only behavior required by `EXERCISE.md`.
- Treat `EXERCISE.md` as the authoritative functional specification.
