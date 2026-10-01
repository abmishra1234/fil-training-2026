# Judge suite: Expense Claims API Challenge

> **Released by the trainer after the code freeze.** Run it once against your frozen commit, then copy the
> result matrix (total / passed / failed per category) into slide 3. Do not change your code after this point.

A black-box suite of 436 test cases. It **starts your service** with the environment
described in `EXERCISE.md` §2, calls it over HTTP, reads its stdout log, and stops it
again. The service is restarted with fresh seed data for every test module. Any language works.

## 1. Set up (once)

```bash
cd judge
python -m venv .venv-judge && source .venv-judge/bin/activate     # Windows: .venv-judge\Scripts\activate
pip install -r requirements.txt
```

## 2. Tell the judge how to start your API: `judge_config.json`

```json
{ "start_cmd": "python -m app", "workdir": "../../my-expense-api", "startup_timeout_seconds": 60 }
```

`workdir` is resolved relative to this folder. Examples of `start_cmd`:

| Stack | start_cmd |
|---|---|
| FastAPI | `uvicorn app.main:app --host 127.0.0.1 --port {port} --no-server-header` |
| Spring Boot | `java -jar target/expense-api.jar --server.port={port}` |
| ASP.NET Core | `dotnet run --project src/ExpenseApi --urls http://127.0.0.1:{port}` |
| Node/Express | `node server.js` (read `process.env.APP_PORT`) |

Build your jar/dll **before** grading. The judge only starts it and does not compile it.

## 3. Run

```bash
python grade.py --team "team-falcon"          # full run, 100 points, about 1-3 minutes
python grade.py token rbac object             # only some categories
python -m pytest tests/test_05_filtering.py -q -x   # plain pytest while debugging
```

Reports: `reports/judge_report.md`, `.html` and `.json`. The `.md` file starts with the **result matrix** (Total · Passed · Failed · Points per category). Copy it into **slide 3**, or paste a screenshot of the `.html`.

## 4. Categories (10 points each)

| Code | Checks | OWASP |
|---|---|---|
| AUTHN | login, token issuance, enumeration, lockout, rate limit | A07, A04 |
| TOKEN | signature, alg pinning, exp/iss/sub, disabled users, token location | A07, A08 |
| RBAC | role checks, server-side roles | A01 |
| OBJECT | BOLA/IDOR, 404-vs-403, self-approval, data scope, excess data | A01 |
| FILTER | filtering, sorting, pagination vs. an independent oracle | functional |
| INPUT | strict validation, injection, mass assignment, content type | A05 |
| WORKFLOW | state machine, threshold, final states, idempotent retries | A06 |
| CONFIG | security headers, CORS, methods, prod hardening, fail-to-start | A02 |
| LOGGING | JSON security events, no secrets in logs | A09 |
| RESILIENCE | hostile input, no 5xx/leaks, request id, size limits, latency | A10, NFR |

## 5. Debugging tips

* A test's docstring is its requirement. Read it together with `EXERCISE.md`.
* Every start writes a log to a temp file `judge-app-*.log`. If start-up fails, the last 2 KB are printed.
* The judge generates a new random `JWT_SECRET` each time. Never hard-code one.
* Rules: don't edit anything in `judge/` or `seed/`.
