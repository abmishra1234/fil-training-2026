# Judge release: run after the code freeze

Unzip next to your project, so that the folders look like this:

```
expense-api/        <- your frozen project
judge-release/
  judge/            <- grade.py, tests, TEST_CATALOGUE.md
  seed/
```

```bash
cd judge-release/judge
python -m venv .venv-judge && source .venv-judge/bin/activate
pip install -r requirements.txt
# edit judge_config.json: start_cmd for your stack, workdir = path to your project
python grade.py --team <your-team-name>
```

Copy the **result matrix** from `reports/judge_report.md` (Total / Passed / Failed / Points per category) into slide 3,
then explain each failure and the fix you would make. Do not change your code. The trainer re-runs your frozen commit.
More detail: `judge/README.md`.
