# Troubleshooting: symptom -> cause -> fix

| Symptom | Likely cause | Fix |
|---|---|---|
| No run appears after push | file not in `.github/workflows/`, or branch filter | check folder name (with the dot) and `on:` branches |
| `refusing to allow ... to create or update workflow` | token lacks Workflows permission | fine-grained token with Contents + Workflows: read/write, or browser login |
| `Invalid workflow file ... error in your yaml syntax on line N` | indentation, tab, missing space after `:` | fix line N, 2 spaces per level; run `actionlint` locally (`pip install actionlint-py`) |
| No "Run workflow" button | no `workflow_dispatch`, or file not on main | add trigger, merge to main |
| `ruff: command not found` | install step missing | `pip install -r requirements-dev.txt` |
| Artifact: `No files were found` | path typo, or earlier step failed | same path as `--junitxml`; `if: always()` |
| Python "3.1" installed | unquoted `3.10` | always quote versions |
| PR stuck "Expected - Waiting for status to be reported" | required check name not produced (renamed / reusable workflow) | edit ruleset check names |
| `GH013: Repository rule violations` on push | ruleset protects main | use the PR routine |
| `JWT_SECRET is not set` in deploy | secret at wrong level/name, or job lacks `environment: staging` | environment secret `JWT_SECRET` on `staging` |
| Deploy not waiting for approval | required reviewers not saved | Settings -> Environments -> staging |
| `Resource not accessible by integration` (403) | GITHUB_TOKEN permission too low | `permissions: contents: write` in release.yml |
| Smoke test FAIL | app refused to start | read the "Show application log" step |
