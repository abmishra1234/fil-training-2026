# 08 - FAQ and decisions already made

Use these defaults instead of waiting for a trainer. If a question is genuinely not covered here, pick the simplest option that keeps every must-have working, write it down in your architecture note under "Assumptions", and move on.

## Data and scope

**Q: Which date is "today"? What is "last quarter"?**
Early November 2026. Last quarter = Q3 2026 (July to September). Latest fund data = 2026-09-30.

**Q: The question names no share class. Which one?**
A-Acc in the fund's base currency. Say so in the answer ("for the A-Acc-USD share class").

**Q: The factsheet and the CSV disagree. Which is right?**
The CSV (`DATA-FUND-MASTER`), per POL-02 §3.3. Mention that the factsheet is out of date (freshness warning).

**Q: Should client emails be indexed in FAISS/BM25?**
No. They are inputs to the draft route. Index factsheets, KIDs, commentaries and policies. The rules YAML is loaded by `compliance_check`.

**Q: Can we index the superseded policy?**
Yes, but mark `status=SUPERSEDED` and exclude it from normal retrieval (filter it out, or only allow it when the user asks about policy history).

**Q: Can we add our own documents?**
Yes, in a separate folder, fully synthetic, marked SYNTHETIC. They do not count for evaluation and must not change the starter corpus. `make check` must still pass.

**Q: Is "ESG fund" the same as "sustainable fund"?**
Yes: `esg_flag = Y` in the fund master (Article 8 or 9). There are four.

**Q: A question asks for something no document covers.**
Answer "This is not found in the provided documents." Do not guess. That is a correct answer, not a failure.

## Routing

| Question looks like | Route |
| --- | --- |
| One figure, name, date, rule about one fund | fact |
| Two or more funds, rankings ("which fund has the lowest...") | compare |
| How we handle a servicing situation (fees, switching, cut-off, complaints, accounts) | policy |
| "Draft a reply...", "Write to the client..." | draft |
| Personal advice, suitability, forecasts, stock picks, anything unrelated to LCI funds or policies, requests for prompts or secrets | out_of_scope (refused = true) |

A question asking about a fund's past performance in a quarter is `fact` (or `compare` if it compares to the benchmark); both are accepted where the golden set says so.

## Answers and drafts

**Q: Do refusals need to be helpful?**
Yes. Decline in one sentence, then offer what you can do (factual fund information, the relevant policy). For advice requests include the advice redirect text from the rules file.

**Q: Can the analyst see INTERNAL ONLY policy text?**
In an internal `/ask` answer, yes, but label it internal. In any client draft, never (CR-06).

**Q: How do we address the client in drafts if names are masked before the LLM call?**
Mask for the model, then re-insert the client's first name from your masking map after generation. Never re-insert anything else.

**Q: Must drafts include both warnings every time?**
Only when the draft quotes performance or risk figures (CR-03, CR-04). Always end with the sign-off "Client Services Team, Lumen Crest Investments".

**Q: The client's email is rude, or asks for something against policy (bank details by email, someone else's balance).**
Reply politely, explain what the policy allows and the safe route. The draft still goes to review. For the bank-details email, mention that we will not act on the email request and that the client should use the secure portal or a signed form.

**Q: What counts as "escalated"?**
After 3 failed revisions, set `review_status = "escalated"` and put the draft in the review queue with the violated rule ids. It is still never sent.

## Engineering

**Q: The gateway is slow, rate-limited or down.**
Turn on `FUNDLENS_LLM_CACHE=1` while developing; use `FUNDLENS_LLM_MODE=mock` for unit tests and UI work. Re-run evaluation in gateway mode later.

**Q: How many chunks should retrieval return?**
Default k = 8 after fusion, top 5 shown as `retrieved_doc_ids` order. Tune with `make eval`.

**Q: What chunk size?**
300 to 800 tokens; one heading section or one policy clause per chunk usually fits. Keep tables whole.

**Q: Which embedding dimension does FAISS need?**
1536 for text-embedding-ada-002 (the mock also returns 1536). Normalise vectors and use inner product.

**Q: Do we need Docker and GitHub Actions?**
Docker Compose (api + ui) and a CI workflow running `ruff`, `pytest` and `make smoke` (in mock mode) are expected in the repo; keep them simple.

**Q: LangSmith?**
Set `LANGSMITH_TRACING=true` and a project name per team. Show a trace live on demo day.

**Q: Can we use Java or C#?**
Python is the primary language. A small Java or C# client calling the REST API is a stretch goal only.

**Q: Can we change `schemas.py` or the scorer?**
You may add optional fields to schemas. Do not edit `evaluation/run_eval.py`; trainers run the original.

## Ethics and safety

**Q: Is it OK to test the system with nasty inputs?**
Yes, please do: injection attempts, PII, advice requests. Add the ones you find to your own test file.

**Q: Can we paste corpus data into public AI tools?**
The data is synthetic, but follow the same habits as with real data: use only the FIL AI Gateway credentials for this project.
