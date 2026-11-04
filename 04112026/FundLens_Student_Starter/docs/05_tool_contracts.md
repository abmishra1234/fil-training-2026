# 05 - Tool contracts (FR-11)

Expose these as LangChain / LangGraph tools with clear docstrings; the model chooses them from the docstring. Every tool result must carry the source id and as-of date so the answer can cite it.

## fund_lookup

```python
fund_lookup(fund: str, share_class: str | None = None, fields: list[str] | None = None) -> list[FundRecord]
```

- `fund`: fund_id, full name or alias ("Global Tech Fund" → F01). Unknown fund → empty list (then say not found).
- `share_class`: "A-Acc", "Y-Acc-USD", ... Partial classes get the fund's base currency. None → A-Acc.
- `fields`: CSV column names. None → a sensible default set (ocf_pct, sri_risk_score, return_1y_pct, return_3y_ann_pct, return_5y_ann_pct).

Example output:

```json
[{"fund_id": "F01", "fund_name": "LCI Global Technology Fund", "share_class": "A-Acc-USD", "isin": "ZZ0000010072",
  "values": {"ocf_pct": 1.89}, "as_of_date": "2026-09-30", "source_doc_id": "DATA-FUND-MASTER"}]
```

## compare_funds

```python
compare_funds(funds: list[str], fields: list[str], share_class: str = "A-Acc") -> list[FundRecord]
```

2 to 4 funds. Also support "all funds" / a filter (for example `esg_flag == "Y"`) so questions like "which ESG fund has the lowest OCF" work. Present the result as a table in the answer.

## calculator

```python
calculate(expression: str) -> float
```

For differences, ratios and rankings, e.g. `round(1.04 - 0.84, 2)`. Parse with `ast`; allow numbers, `+ - * / ( )`, `round`, `min`, `max`, `abs`. Never `eval()` model output.

## policy_search

```python
policy_search(query: str, policy_type: str | None = None, k: int = 4) -> list[dict]
# -> [{"doc_id": "POL-01-v3.0", "section": "§4.2", "status": "ACTIVE", "effective_date": "2026-07-01", "text": "4.2 The second and any later switch ..."}]
```

Only ACTIVE policies by default.

## compliance_check

```python
compliance_check(draft: str, client_email: str | None = None) -> ComplianceResult
# -> {"passed": false, "violated_rule_ids": ["CR-03", "CR-04"], "findings": [{"rule_id": "CR-03", "span": "missing: risk_warning", "severity": "block"}]}
```

Runs every rule in `corpus/rules/compliance_rules.yaml` (see the comments at the top of that file for how each `check_type` works). Return `violated_rule_ids` so the revise node knows exactly what to fix (each rule has a `fix_hint`). Target on `evaluation/seeded_drafts_dev.jsonl`: flag at least 9 of the 10 non-compliant drafts and pass all 4 clean ones.

## Tool rules for the agent

- Numbers in answers come from `fund_lookup` / `compare_funds` / `calculator` or from a cited chunk. The groundedness check should fail any number that does not.
- Tool errors become a short message in state, not an exception that kills the graph.
- Log every tool call (name, arguments, result size, latency) in `audit_events`.
