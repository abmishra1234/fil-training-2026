# Decision Log — Counterstrike Lite (team: ______)

Rename to `DECISION_LOG.md`. Keep it current: when a decision changes, update the entry and note why.
Status: **Accepted** / **Provisional** / **Superseded by DL-xx**.

| ID | Decision (one line) | Status |
|----|---------------------|--------|
| DL-01 | Orchestration style | |
| DL-02 | Agent boundaries | |
| DL-03 | What the LLM may and may not decide | |
| DL-04 | Version matching | |
| DL-05 | Implementing and explaining the risk policy | |
| DL-06 | Grounding / validation of LLM output | |
| DL-07 | Prompt-injection defence | |
| DL-08 | LLM access + offline stand-in for CI | |
| DL-09 | Evaluation and the CI gate | |
| DL-10+ | (your own) | |

---

## DL-01 — Orchestration style
**Context.** _What problem forces a choice here?_

| Option | For | Against |
|---|---|---|
| A. | | |
| B. | | |
| C. | | |

**Decision.**
**Consequences.** _What becomes easier, harder, or must now be tested?_
**Revisit when.**

<!-- Copy the block above for each entry. Prompts to think about: -->
<!-- DL-02: how many agents, what does each own, what typed object does each hand over? -->
<!-- DL-03: list every output field and say whether code or the LLM produces it. -->
<!-- DL-04: how do you compare "2.9" vs "2.17"? what about "1.1.1w"? what happens to an unparseable version? -->
<!-- DL-05: where does the policy live, how is it tested at the band boundaries, how does an alert explain its score? -->
<!-- DL-06: what if the model returns a version that is not in the bulletin? non-JSON? an unknown product? -->
<!-- DL-07: what layers stop a bulletin that says "ignore previous instructions"? how do you prove it in CI? -->
<!-- DL-08: how do you keep CI offline and deterministic while still supporting a real model? -->
<!-- DL-09: which metrics, which thresholds, what blocks a merge, what is uploaded? -->
