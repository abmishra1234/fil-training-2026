# Counterstrike Lite — student pack

Start with **ASSESSMENT.md** (problem, constraints, scope, deliverables, rubric).

```
ASSESSMENT.md                 the brief
DECISION_LOG_TEMPLATE.md      fill in -> DECISION_LOG.md
data/                         synthetic feed, inventory, KEV list, aliases, gold labels
tests/test_contract.py        public contract tests (must pass unchanged)
src/counterstrike/cli.py      entry point stub - replace with your fleet
.github/workflows/ci.yml      starter CI - extend it (deliverable D4)
```

```bash
pip install -e ".[dev]"
pytest tests/test_contract.py     # fails until the fleet is built
```

CI run on main: _add link here_
