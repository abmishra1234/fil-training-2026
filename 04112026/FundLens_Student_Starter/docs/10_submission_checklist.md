# 10 - Submission checklist (end of Day 6)

Tick every box before Gate 3. Bring this list to the demo.

## Repository

- [ ] One-command setup works from a clean clone (`make setup && make check`)
- [ ] `.env.example` present, `.env` NOT committed, no keys anywhere in code, logs or prompts
- [ ] `make test` green; unit tests cover tools, compliance_check, PII masking and RRF
- [ ] `ruff check` clean
- [ ] Docker Compose (api + ui) and a CI workflow running lint, tests and `make smoke` in mock mode
- [ ] README: how to run ingest, API, UI, eval; team members and roles
- [ ] Starter corpus unchanged (`make check` says "intact")

## Functionality (must-haves)

- [ ] UC1-UC7 all work through the UI and the API
- [ ] Every factual sentence cited `[doc_id §section]`; "not found in the provided documents" when unsupported
- [ ] Numbers come only from tools or cited chunks
- [ ] Freshness warning on stale sources
- [ ] Drafts pause for review; approve / edit / reject works; edited text is re-checked
- [ ] PII masked before LLM calls and in the audit log; secrets blocked
- [ ] Injection attempts in emails and documents are ignored
- [ ] LangSmith trace per request; audit log with question, route, tools, sources, reviewer decision

## Evaluation report (`reports/`)

- [ ] Baseline, + MQR/RRF and full-agent reports side by side
- [ ] Final dev report with `--judge`, meeting every pass threshold
- [ ] Compliance catch rate on seeded drafts
- [ ] Three failure analyses (what, why, fix, result)
- [ ] Latency p95 and LLM calls per fact question

## Architecture note (max 2 pages)

- [ ] Graph diagram (nodes, edges, loops, interrupt)
- [ ] Prompts used (router, answer, grader, draft, revise), with versions
- [ ] Key design trade-offs and assumptions

## Demo (Day 7, 20 minutes)

- [ ] 5-minute backup recording uploaded
- [ ] Live: UC1 to UC7, one LangSmith trace open, one draft approved and one rejected in the review queue
- [ ] Live hidden-set run: trainers give you `golden_set_hidden.jsonl`; you run `make predict GOLDEN=<path> DRAFTS=<path>` and the trainers run `run_eval.py`
- [ ] Every member can explain any part of the code
