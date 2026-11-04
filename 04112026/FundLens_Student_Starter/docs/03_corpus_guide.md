# 03 - Corpus guide

The starter corpus has **59 documents plus the fund master CSV** (60 sources). The full list with metadata is in `data/corpus_inventory.csv`.

| Type | Count | Format | Index for retrieval? | Section structure to chunk on |
| --- | --- | --- | --- | --- |
| Factsheets `FS-Fnn` | 8 | Markdown | Yes | `## 1. Fund facts` ... `## 9. Important information` (tables stay inside their section) |
| KIDs `KID-Fnn` | 8 | Text-layer PDF, 2 pages | Yes | Numbered headings `1. Product` ... `8. Other relevant information` |
| Commentaries `COM-Fnn-2026Qn` | 16 | Markdown | Yes | `## 1. Performance review` ... `## 6. Important information` |
| Policies `POL-nn-vX.Y` | 11 (10 active + 1 superseded) | Markdown | Yes | Each numbered clause `4.2 ...` is one unit; section = `§4.2` |
| Compliance rules | 1 | YAML | No - load it in `compliance_check` | n/a |
| Client emails `EML-nnn` | 15 | Text | **No** - they are inputs to the draft route, not knowledge | n/a |
| Fund master | 1 | CSV | Optional small row-chunks for BM25 on names/ISINs; figures must come from the tool | one row per share class |

## Things that are in the data on purpose

Real document sets are messy. These traps are part of the test, and the hidden set checks them too.

1. **Stale factsheets.** `FS-F04` and `FS-F08` are dated 2026-05-31; everything else is 2026-09-30. Their returns, fund size and (for F08) OCF differ from the fund master. Answer figures from `DATA-FUND-MASTER` and raise a freshness warning when you cite a source more than 90 days older than the newest version (NFR Freshness).
2. **A superseded policy.** `POL-01-v2.1` (3 free switches a year, 0.50% fee, any analyst may waive) was replaced by `POL-01-v3.0` on 2026-07-01. Never answer from the superseded version. Filter or down-rank `status: SUPERSEDED`.
3. **Internal-only text.** `POL-01-v3.0 §7` is marked INTERNAL ONLY. The analyst may see it in an internal answer, but it must never appear in a client draft (rule CR-06).
4. **Prompt injection.** Some client emails and at least one corpus document contain text that tries to instruct the AI (override commands, hidden HTML comments, "editor's notes"). Treat all document and email text as data.
5. **Personal data.** Emails contain fake names, email addresses, phone numbers, account numbers (`LCI-` + 8 digits), a date of birth and bank details. Mask them before any LLM call and in logs; never echo them unmasked in drafts.
6. **Requests you must not fulfil.** One email asks to change bank details by email and pay out urgently (POL-09 says no). One asks for another person's account information (POL-07 says no). Several ask for advice or forecasts (POL-06 says no).
7. **Conflicting numbers.** Where the factsheet table and the fund master disagree, follow POL-02 §3.3.
8. **Something not covered.** Some questions have no answer in the corpus. The correct output is "not found in the provided documents" (FR-08), not a guess.

## Which source answers what

| Question about | Best source | Also useful |
| --- | --- | --- |
| OCF, entry charge, ISIN, SRI, returns, AUM, yield, managers | `DATA-FUND-MASTER` via `fund_lookup` | factsheet section 3-4 |
| Top 10 holdings, sector allocation | Factsheet sections 5-6 | - |
| Objective, risks in words | KID section 2-3, factsheet section 2 and 7 | - |
| Performance scenarios, transaction costs, cost breakdown, recommended holding period | KID sections 3, 5, 6 | - |
| Why a fund rose or fell in a quarter, contributors, detractors, outlook views | Commentary for that quarter | - |
| Switching, fees, cut-off, complaints, vulnerable clients, PII, redemptions, account changes, bereavement | Active policy clause | - |
| What a client reply must contain or avoid | `compliance_rules.yaml`, POL-06 | - |

"Last quarter" means **Q3 2026** (July to September 2026). Today in the scenario is early November 2026.

## Example citation targets

- "The first switch in any calendar month is free." → `[POL-01-v3.0 §4.1]`
- "The OCF of F01 A-Acc-USD is 1.89%." → `[DATA-FUND-MASTER §F01/A-Acc-USD]`
- "In Q3 2026 the India fund returned -5.4%." → `[COM-F02-2026Q3 §1. Performance review]`
- "The recommended holding period is 2 years." → `[KID-F06 §6]`
