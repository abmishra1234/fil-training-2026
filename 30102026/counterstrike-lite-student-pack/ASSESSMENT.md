# Assessment — Counterstrike Lite: a mini agent fleet for CVE triage

*Derived from the capstone "Project Counterstrike: Agent Fleet". Same idea, sized for one working day.*

| | |
|---|---|
| Team | 2 developers |
| Time box | 6 hours of build + 10-minute demo |
| Language | Python 3.10+ |
| Hand-in | Git repository (this pack as the starting point) with a green CI run on `main` |

---

## a. Problem statement

New vulnerabilities are published every day — some as tidy structured records, many as free-text vendor bulletins. Today a security analyst reads each one, checks by hand whether the company runs the affected software at an affected version, decides how urgent it is for *this* company, and emails the owning team. It is slow and error-prone: patched systems get flagged, exposed systems get missed, and urgency is guessed.

**Build a small fleet of cooperating agents that does this end to end for one batch:**

1. **Ingest** a feed of advisories, a KEV-style list of actively exploited CVEs, and the asset inventory.
2. **Extract** the affected product, affected version range and fixed version from each advisory. Structured records can be mapped by code; free-text bulletins need an LLM.
3. **Correlate** each advisory against the inventory and keep only assets running an affected version.
4. **Score** each match by real exposure — not CVSS alone — and assign a priority **P1–P4** with an SLA.
5. **Write** one alert per affected asset that its owner can act on without opening the advisory, with evidence for every fact.

The fleet must be **trustworthy**: it must not invent versions, must not be steered by text inside the feed, and must say "I don't know" (route to a human) instead of guessing.

## b. Constraints

| # | Constraint | Why |
|---|---|---|
| C1 | Python 3.10+. Any agent framework (LangGraph, CrewAI, plain Python) is allowed; justify it in the decision log. | Cohort stack; the choice is part of what we assess. |
| C2 | **At least 3 distinct agents** with clear single responsibilities, communicating through typed data (e.g. pydantic models), not free text. | It is a multi-agent assessment. |
| C3 | **CI must pass with no LLM key and no network** beyond the package index. Provide a deterministic stand-in (fake/mock LLM) behind an interface, plus a real backend selectable by config. | Reproducible grading; enterprise runners have no model access. |
| C4 | The LLM may *read and word*. **Matching, scoring, priority, SLA and owner must be computed by code.** | Decisions must be reproducible and explainable. |
| C5 | Every version an LLM returns must be traceable to the source text. Unverifiable output goes to `needs_human.json`. | No hallucinated ranges. |
| C6 | Feed text is **untrusted input**. Instructions inside it must not change behaviour. | One fixture contains a prompt-injection attempt. |
| C7 | Input files are read-only. Outputs go only to `--out`. No email, chat or ticket is sent. | Safe by construction. |
| C8 | Use only the provided synthetic data (`CVE-2099-xxxx`). No live NVD calls. | Offline, identical for every team. |
| C9 | Secrets (API keys) only via environment variables / CI secrets, never committed. | Basic hygiene. |

## c. Scope

**In scope**
- One batch run over the files in `data/`: `advisories.json` (8 items: 3 structured, 5 free text), `inventory.json` (8 assets), `kev.json`, `aliases.json`.
- Version-range logic including inclusive/exclusive bounds and odd versions such as `1.1.1w`.
- The **risk policy** below (set by the security office, so every team's priorities are comparable). Implement it exactly in code:

  | Factor | Points |
  |---|---|
  | CVSS base score | 0 – 10 |
  | CVE is in `kev.json` | +2.0 |
  | Asset is internet-facing | +1.5 |
  | Criticality: critical / high / medium / low | +2 / +1 / 0 / −1 |

  Score is floored at 0. **P1 ≥ 12 (SLA 24 h) · P2 ≥ 9 (168 h) · P3 ≥ 6 (720 h) · P4 < 6 (2160 h).** Keep the per-factor breakdown so the alert can explain its priority.
- Outputs (the **contract**, checked by `tests/test_contract.py`):
  - `out/alerts.json` — a list of alerts, each with at least: `alert_id, cve_id, asset_id, service, component, installed_version, fixed_version, risk_score, priority, sla_hours, owner, summary, remediation, evidence` (non-empty list).
  - `out/needs_human.json` — list of `{advisory_id, stage, reason}`.
  - `out/run_report.json` — counts and a per-agent trace.
- Command: `python -m counterstrike run --data data --out out`.
- Unit tests, an evaluation against `data/gold/expected_alerts.json`, and CI.

**Out of scope**
- Live feeds, scheduling, databases, UIs, dashboards, Docker images.
- Sending notifications or creating tickets.
- Exploitability research, EPSS, SBOM generation, patching anything.
- Multiple batches, deduplication across runs, history.

**Gold labels (public)** — `data/gold/expected_alerts.json` lists the alerts and priorities we expect, pairs that must *not* alert, the advisory that must be routed to a human, and the injection fixture. Hidden grading reruns your fleet on a second fixture set with the same shape, so do not hard-code IDs.

## d. Decision logs (required)

Fill `DECISION_LOG_TEMPLATE.md` as you go (rename it `DECISION_LOG.md`). Every entry needs: context, at least two options considered, the decision, its consequence, and what would make you revisit it. **Mandatory entries:** orchestration style, agent boundaries, what the LLM is allowed to decide, version matching, how the risk policy is implemented and explained, grounding/validation, prompt-injection defence, LLM access and the offline stand-in, evaluation and CI gate.

## e. GitHub Actions CI (required)

`.github/workflows/ci.yml` is a starter that installs the project, runs `ruff`, and runs the public contract tests. Extend it so that on every push and pull request:

1. Lint and format checks pass.
2. Unit tests run with a coverage floor (≥ 80% recommended).
3. A job runs the fleet with your offline LLM stand-in and **fails the build** unless the output matches the gold labels (precision, recall, priority accuracy) and the safety checks hold.
4. The `out/` folder is uploaded as a workflow artifact.
5. (Bonus) An optional, manually triggered job runs the fleet against a real model using repository secrets.

Use current major versions of actions (e.g. `actions/checkout@v7`, `actions/setup-python@v6`, `actions/upload-artifact@v7`) and least-privilege `permissions`.

---

## Deliverables

| ID | Deliverable | Done when |
|---|---|---|
| D1 | Working fleet | `python -m counterstrike run` produces the three output files; contract tests pass |
| D2 | Tests | Unit tests per agent, plus tests for: hallucinated version rejected, non-JSON model output handled, injection not obeyed, no-match path |
| D3 | Decision log | All mandatory entries present and specific to your code |
| D4 | CI | Workflow as in (e); a green run on `main` linked in the README |
| D5 | Demo | 10 minutes: architecture, one alert traced to its evidence, the injection fixture, the CI run |

## Evaluation rubric (100 points)

| Area | Points | What we look for |
|---|---|---|
| Correctness vs gold (public + hidden fixtures) | 30 | Right alerts, no false alerts on patched/out-of-range assets, right priorities |
| Agent design | 15 | Clear responsibilities, typed contracts, sensible routing (incl. short-circuits) |
| Trustworthiness | 20 | Grounding, human-queue routing, injection resistance, LLM never decides priority |
| Tests | 10 | Meaningful unit + failure-path tests; coverage |
| CI | 10 | Gate actually blocks regressions; artifact; secrets handled correctly |
| Decision log | 10 | Real options weighed; consequences named |
| Demo & code quality | 5 | Readable code, README, clear explanation |

**Automatic fail:** any alert priority set by an LLM; committed API keys; CI that cannot run without a model key.

## Clarifications already decided (so you don't have to ask)

- *"Affected"* means the installed version is inside the advisory's affected range. A bulletin that says a product line is "not affected" produces no alert for that line.
- Aliases map advisory product names to inventory component names (`log4j2` → `log4j-core`).
- If a bulletin gives no product you can map or no version range, do not guess — route it to `needs_human`.
- Ties in ordering do not matter for grading; content does.
