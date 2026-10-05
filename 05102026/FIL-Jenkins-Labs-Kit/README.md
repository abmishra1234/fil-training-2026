# FIL Jenkins Hands-on Labs - classroom kit

Follow the slide deck `Jenkins_Hands-on_Labs_FIL.pptx` step by step. Every step has a DO and a VERIFY.

| Part | Folder | Result |
|---|---|---|
| 0 Setup | `00-jenkins-setup/` | `docker compose up -d --build` -> Jenkins LTS 2.580.1 + Python 3 at http://localhost:8080 (admin / admin123, lab only) |
| Lab 1 | `lab1/starter/expense-api` + `lab1/solution/Jenkinsfile.step1..5` | Setup -> Lint -> Test -> Build -> Deploy pipeline |
| Lab 2A | `lab2/solution/fil-jenkins-lib` (+ `-v1.1.0`), `lab2/starter/unit-converter` | Jenkins Shared Library reused by 2 projects |
| Lab 2B | `lab2/solution/python-ci-action`, `lab2/solution/*/.github/workflows/ci.yml` | Composite GitHub Action reused by 2 repos |

## Pinned versions
Jenkins `2.580.1-lts-jdk21` · ruff `0.16.10` · pytest `9.1.1` · httpx `0.28.1` · FastAPI `0.142.2` · `actions/checkout@v7` · `actions/setup-python@v7` · Python 3.11-3.13.

## What was verified while building this kit
- Lab project: `ruff check app tests scripts` -> All checks passed; `pytest` -> 13 passed; `pip wheel . --no-deps -w dist` -> expense_api-1.0.0 wheel;
  `scripts/deploy_local.sh` + `scripts/smoke_test.py` -> 4/4 PASS, redeploy stops the old process; break-and-fix exercises produce exactly the errors shown in the deck.
- unit-converter: lint + format check + 7 tests + wheel pass; the Lab 2B break produces F401 at converter/__init__.py line 6.
- All Jenkinsfiles and Shared Library Groovy files parse (npm-groovy-lint: 0 syntax errors).
- Workflows pass actionlint 1.7.12; the composite action's shell steps were executed locally on both projects.
- Not executable in the build sandbox: a live Jenkins controller and GitHub-hosted runners. **Trainer: do one full dry run on the FIL network before class.**

If plugin/image downloads are blocked on the class network: build once elsewhere, `docker save fil-jenkins-lab:1.0 -o fil-jenkins-lab.tar`, share, then `docker load -i fil-jenkins-lab.tar` and `docker compose up -d` (no `--build`).
