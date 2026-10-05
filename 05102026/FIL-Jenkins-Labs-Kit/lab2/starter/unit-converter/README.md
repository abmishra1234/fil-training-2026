# unit-converter

Second Python project used to prove that `fil-jenkins-lib` is reusable.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
ruff check converter tests && pytest -q
```
