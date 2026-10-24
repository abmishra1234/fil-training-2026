# Judge Tests: Mini AI Gateway (Week 06 assessment)

30 judge tests (78 test cases) check every requirement of the brief: acceptance rows,
the three secret types, extensibility, fail-closed behaviour, no-leak logging, the
20 ms budget, and end-to-end behaviour in Basic RAG, MQR, MQR + RRF, Agentic RAG and
the HTTP API.

Everything runs **offline**: the LLM and the embedding model are replaced by a recorder
(`fakes.py`), so you need no credentials and the tests can see every prompt that would
have been sent to the model.

## Run it

```bash
# from the project root (the folder with app/ and data/)
pip install -r requirements.txt
python judge_tests/run_judge.py --student "Your Name"
```

Submit `judge_tests/reports/judge_report.md`. For a quick loop while you work:
`python -m pytest judge_tests -q`

The full run takes about 30-60 seconds.

## The one file you edit: `adapter.py`

The judge does not know your module or class names. `adapter.py` maps its small
vocabulary onto your code. In the student pack every function starts as
`NotImplementedError`: fill each one in so it calls your implementation. (The
trainer's copy is wired to the reference solution in `app/gateway`.)

| Function | You return |
|---|---|
| `TYPE_CREDENTIAL`, `TYPE_CARD`, `TYPE_CODENAME` | the finding keys you use for the three types |
| `make_passage(chunk_id, text)` | one of your Passage objects |
| `check(query, passages)` | your default gateway's result (the minimum interface from the brief) |
| `result_view(result)` | `{decision, safe, safe_ids, dropped, findings}` as plain values |
| `write_codename_config(dir, names)` | path of a config file in your format listing exactly `names` |
| `make_custom_detector(type, count_fn)` | a new secret type, plugged in the way your design intends |
| `make_gateway(codenames_path, extra_detectors)` | a gateway object with `.check(...)` |
| `make_rag_service(cfg, embeddings, gateway)` | your `RagService`; it must use `gateway` when given |
| `make_agent_service(rag)` | your `AgentService`, using the same gateway |

Do not put detection logic in the adapter. If a well-designed gateway is in place,
every adapter function is one to three lines.

## What the judge expects (read before you start)

1. Your **default config file** lists at least `Project Falcon` and `Project Monsoon`.
2. Replies are exact:
   - query blocked: `Your request contains restricted content and was not processed.`
   - every passage dropped: `I could not find this in the approved sources.`
3. **No LLM call** of any kind for a blocked query. MQR query rewriting, the agent's
   router and contextualize steps are LLM calls too.
4. A dropped passage never reaches **any** LLM call. In the agent that includes
   `assess` and `check`, not only `generate`.
5. The secret is never in an API response. That includes the echoed question, the
   retrieval inspector `pool`, `sources` and the agent trace.
6. Logs and the console carry the secret **type and count**, never the text, and that
   includes exception messages.

## Interpretation choices (where the brief is open)

| Question | Judge's position |
|---|---|
| Some passages dropped, some left: `ALLOW` or `BLOCK_CONTEXT`? | Both accepted by the unit tests. End to end, the remaining passages **must** still reach the LLM. |
| `findings` for a blocked query | Must count the query's secret type (≥ 1). Passages need not be scanned. |
| Zero-count keys in `findings` | Ignored. |
| Codename split by a line break or double space | Still the codename (chunked text wraps lines). |
| A 12-digit or 20+ digit number | Not a card (the brief says 13 to 19 digits). |
| Error inside the gateway after some passages were scanned | `BLOCK_ERROR` and **nothing** released. Dropping only the failing passage is fail-open. |
| Talking about secrets ("passwords and tokens must never be committed") | Not a secret. The whole `data/docs` handbook must pass clean. |

## Test catalogue

| # | Group | Requirement verified |
|---|---|---|
| JT01 | A Acceptance | No secret: ALLOW, all passages in order |
| JT02 | A Acceptance | Secret in one passage: only that one dropped |
| JT03 | A Acceptance | Secret in every passage: BLOCK_CONTEXT, exact per-type counts |
| JT04 | A Acceptance | Secret in the query (each type): BLOCK_QUERY |
| JT05 | A Acceptance | Query and passage secrets: query block wins |
| JT06 | A Acceptance | Gateway error, even mid-scan: BLOCK_ERROR, nothing released |
| JT07 | A Acceptance | Error path does not leak the text it failed on |
| JT08 | B Credentials | Known key prefixes (sk-…, AKIA…) in any position, passage and query |
| JT09 | B Credentials | password / secret / api_key followed by = or :, any case, NAME_ prefix |
| JT10 | B Credentials | No false positives on policy text and the real handbook |
| JT11 | B Credentials | Distinct credentials counted once each |
| JT12 | C Cards | Spaces, dashes, plain, Amex 4-6-5, Discover, MasterCard |
| JT13 | C Cards | 13 and 19 digits in, 12 digits out |
| JT14 | C Cards | Luhn failures are not cards |
| JT15 | C Cards | Phones, dates, amounts, UTRs, tickets, versions are not cards |
| JT16 | C Cards | Two cards counted, cards at text edges and in brackets |
| JT17 | D Codenames | Case-insensitive, possessive, punctuation |
| JT18 | D Codenames | Whole phrase only (Falconry, Falcone, single words) |
| JT19 | D Codenames | List comes from the config file, not code |
| JT20 | D Codenames | Config entries are literal text (regex characters escaped) |
| JT21 | D Codenames | Codename split by whitespace / line break |
| JT22 | D Codenames | Mixed types, exact counts |
| JT23 | E Design | New secret types plug in without core changes |
| JT24 | E Design | Result contract: same objects, order, purity, stateless |
| JT25 | E Design | Empty input, Unicode, very large input |
| JT26 | F Constraints | Logs and console never hold secret text; blocks are audited by type |
| JT27 | F Constraints | < 20 ms median: 1 query + 5 × 2,000-char passages |
| JT28 | F Constraints | < 20 ms on adversarial input, no over-blocking of look-alikes |
| JT29 | G End to end | Secret query: 0 LLM calls, exact reply, no echo (6 entry points) |
| JT30 | G End to end | Secret passages: partial, all, gateway error, across 4 pipelines |

A test scores 1 point only if all its cases pass. Score = passed tests / 30.

## Files

| File | What |
|---|---|
| `adapter.py` | **edit this**: maps the judge onto your code |
| `run_judge.py` | runs everything, writes `reports/judge_report.md` + `.json` |
| `conftest.py`, `fakes.py`, `samples.py` | fixtures, offline LLM recorder, synthetic secrets (do not edit) |
| `test_01` … `test_07` | the 30 tests |

All secrets in these files are synthetic test values.
