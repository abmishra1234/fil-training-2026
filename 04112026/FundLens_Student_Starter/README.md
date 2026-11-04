# FundLens Capstone - Student Kit

> All data in this kit is **SYNTHETIC**. The fund house "Lumen Crest Investments" (LCI), its funds, ISINs, companies, people, clients and figures are invented. They are formatted to look like a real fund range, but none of it is real FIL, client or market data. Never put real data into this project.

You have **7 working days** in a team of **2 to 3**. You will build FundLens, a text-only agentic RAG copilot that answers fund and policy questions with citations, drafts client replies, checks them against compliance rules and holds them for human approval.

This kit has everything you need to work without waiting for a trainer: the data, the rules, a starter repo, the evaluation scripts and the answers to common questions. When something is unclear, check `docs/08_faq_and_defaults.md` first. It lists the decisions already made for you.

## Start here (first hour)

1. Read `docs/01_problem_brief.md` (10 minutes). The full requirements are in `docs/00_FundLens_Capstone_Requirements.docx`.
2. Skim `docs/09_domain_primer.md` if terms like OCF, SRI, KID, ISIN or share class are new to you.
3. Open `starter/README_STARTER.md` and follow "First 30 minutes". Run `make check` until it prints ALL GOOD.
4. Read `docs/07_seven_day_plan.md` and split the work in your team.

## What is in the kit

| Folder / file | What it is | Used for |
| --- | --- | --- |
| `corpus/factsheets/` | 8 monthly fund factsheets (Markdown). 2 are deliberately stale | UC1, UC2, UC5 |
| `corpus/kids/` | 8 Key Information Documents (text-layer PDF) | UC1, UC5 |
| `corpus/commentaries/` | 16 quarterly commentaries, Q2 and Q3 2026 (Markdown) | UC4 |
| `corpus/policies/` | 10 servicing policies + 1 superseded version (Markdown, numbered clauses) | UC3, UC4 |
| `corpus/rules/compliance_rules.yaml` | Machine-readable communication rules | compliance_check tool |
| `corpus/client_emails/` | 15 sample client emails with fake personal data | UC4, guardrails |
| `data/fund_master.csv` | 8 funds x 4 share classes: ISIN, OCF, SRI, returns, AUM... | fund_lookup / compare_funds tools |
| `data/fund_aliases.json` | Names clients use for each fund | fund name resolution |
| `data/corpus_inventory.csv` | One row per document with its metadata | ingestion checks |
| `evaluation/golden_set_dev.jsonl` | 40 questions with expected answers | your evaluation |
| `evaluation/golden_set_smoke10.jsonl` | 10-question subset | CI smoke test |
| `evaluation/seeded_drafts_dev.jsonl` | 14 draft replies (10 non-compliant, 4 clean) | compliance catch rate |
| `evaluation/run_eval.py`, `judge_prompt.md` | The scorer the trainers also use | `make eval` |
| `starter/` | Skeleton repo: contracts, LLM client (gateway + offline mock), stubs, scripts, Makefile | your code |
| `docs/` | Brief, data dictionary, corpus guide, API and tool contracts, evaluation guide, plan, FAQ, primer, submission checklist | reference |
| `MANIFEST.sha256` | Checksums of the starter corpus | proves you did not edit it |

## Rules of the game

- Keep the starter corpus unchanged. `make check` verifies it against `MANIFEST.sha256`. You may add your own extra synthetic documents in a separate folder, but they do not count for evaluation.
- Every number in an answer must come from a tool or a cited chunk.
- No draft may reach "approved" without a reviewer action.
- Demo day uses a **hidden** golden set of 40 questions written the same way as the dev set, plus hidden seeded drafts. Do not overfit to the dev questions; make the system general.
- Anything outside use cases UC1 to UC7 is out of scope.

## Documents in `docs/`

| File | Read when |
| --- | --- |
| `01_problem_brief.md` | Day 1, first |
| `02_data_dictionary.md` | Building ingestion and tools |
| `03_corpus_guide.md` | Building ingestion; before writing prompts |
| `04_api_contract.md` | Building the API and UI |
| `05_tool_contracts.md` | Building tools and the agent |
| `06_evaluation_guide.md` | Day 2 onward, every day |
| `07_seven_day_plan.md` | Day 1 planning, daily stand-up |
| `08_faq_and_defaults.md` | Whenever you are unsure |
| `09_domain_primer.md` | Day 1 if the finance terms are new |
| `10_submission_checklist.md` | Day 6 evening |
