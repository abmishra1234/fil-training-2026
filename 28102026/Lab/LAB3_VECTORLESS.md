# Lab 3 · Vectorless RAG: retrieval as reasoning

FIL Graduate AI Cohort · builds on Lab 1 (Basic RAG → MQR → RRF) and Lab 2 (Agentic RAG).
Same app, same handbook, same two models. Nothing from Lab 1 or Lab 2 is thrown away.

**Time:** about 3 hours · **Models:** `azure/gpt-6-luna` only (vectorless never calls `azure/text-embedding-ada-002`)

---

## 1. Why this lab

Every retriever you built so far starts the same way: cut the handbook into 500-character
chunks, turn each chunk into 1,536 numbers with ada-002, and find the chunks whose numbers
are closest to the question's numbers. That finds what **sounds** like the question.

A human expert does something else. They open the table of contents, think *"error codes live
in the payments runbook"*, open that chapter, pick the section, and read it in full.

**Vectorless RAG** copies the expert:

```
              question
                 │
 level 1   LLM reads 12 document titles + summaries ──► picks ≤ 3 documents   ("04 payments runbook")
                 │
 level 2   LLM reads their sections + summaries     ──► picks ≤ 4 sections    ("04.4 PAY-E4035 …")
                 │
           FULL text of the picked sections ──► Lab 1 grounded prompt ──► answer with [n] citations
```

No chunking, no embeddings, no FAISS. The index is the handbook's own outline, and the
navigation path (with the LLM's one-line reasoning at each level) explains *why* each passage
was retrieved.

By the end you can answer, with your own numbers: **is vectorless RAG better than what we
built in Lab 1, and is it always better?**

## 2. The tree index of our handbook

```
root  NovaPay employee handbook
 ├─ [01] NovaPay Leave Policy (HR-POL-01)                   one node per FILE ("# " heading)
 │    ├─ [01.0] Overview                                    text before the first "## "
 │    ├─ [01.1] Earned leave                                one node per SECTION ("## ")
 │    └─ … [01.5] Applying for leave
 ├─ [04] Payments Platform Error Codes (ENG-RUN-PAY)
 │    ├─ [04.1] PAY-E4031 - Settlement batch rejected after cut-off
 │    ├─ [04.4] PAY-E4035 - Signature mismatch on bank file
 │    └─ …
 ├─ [11] NovaPay Engineering Glossary                       no "## " → the document is a leaf
 └─ … 12 documents · 58 leaves
```

Every node carries a **signpost**: a one-sentence summary written once by the LLM (12 calls,
one per document, cached on disk). At question time the navigator reads only ids, titles and
signposts. It reads full text only for the leaves it picks.

## 3. Setup

Same as Lab 2. Two additions to `.env` (defaults shown, all optional):

```ini
VECTORLESS_MAX_DOCS=3          # documents the navigator may open at level 1
VECTORLESS_MAX_SECTIONS=4      # sections it may pick at level 2
VECTORLESS_MAX_STEPS=3         # hard cap on navigation LLM calls per question
VECTORLESS_SUMMARIES=llm       # llm | extractive | none (titles only)
VECTORLESS_CACHE=data/.cache/tree_summaries.json
```

```bash
pip install -r requirements.txt     # no new packages
pytest                              # starter: 14 failed, 50 passed (all Lab 1 + Lab 2 tests pass)
uvicorn app.main:app --reload --port 8000
```

The app runs before you write any code: the Lab 1 and Agentic tabs work, and the new
**Vectorless** mode answers `501 · TODO V1` until you implement it.

## 4. Part A · Build it (TODO V1–V4, about 90 minutes)

| TODO | File | Function | What it teaches | Tests |
|---|---|---|---|---|
| V1 | `app/vectorless/tree.py` | `build_tree()` | The index is the document's own structure. Free to build. | V01–V03 |
| V2 | `app/vectorless/tree.py` | `summarize_document()` | Signposts: one LLM call per document, never crash indexing | V04–V06 |
| V3 | `app/vectorless/navigator.py` | `parse_selection()` | Never trust LLM output: validate every id | V07 |
| V4 | `app/vectorless/navigator.py` | `tree_search()` | Retrieval as a bounded reasoning loop, with a safety net | V08–V11 |

Then V12–V14 (API, evaluation, resilience) turn green with no extra code. Read the docstring
of each function: it is the specification, and the tests check every rule in it.

### V1 · `build_tree()`: parse the outline (no LLM)

Read each `.md` file line by line. `# ` is the document title, `## ` starts a section, and
everything else is text of the current section. Text before the first `## ` becomes an
`Overview` section (id `.0`). A file with no `## ` is a single leaf.

*Checkpoint A:* `pytest -k "V01 or V02 or V03"` is green. Then open **Tree index** in the UI
(it shows titles only until V2 is done). Does it look like the table of contents?

*Think:* V02 checks that **no line of text is lost**. What would a lost line cost you at
question time?

### V2 · `summarize_document()`: write the signposts

One `chat_complete()` call per document with `prompts.TREE_SUMMARY`. Parse the JSON with
`parse_json()` from Lab 2. Every node whose summary is missing, blank or not a string falls
back to `extractive_signpost()`. A broken reply must never break indexing.

*Checkpoint B:* `pytest -k "V04 or V05 or V06"` is green. In the UI, open **Tree index** and
press **LLM summaries**. Read five signposts: could **you** pick the right section from the
signpost alone? If not, the navigator cannot either. Which facts are missing?

### V3 · `parse_selection()`: never trust the reply

The model may answer `"04"`, `"4"`, `4`, `"[04]"` or an id that does not exist. Map each item
to a real id with `_canon()`, drop inventions and duplicates, keep the order, and cap the count.

*Checkpoint C:* `pytest -k V07` is green.

### V4 · `tree_search()`: the navigation loop

```
frontier = the 12 documents
for level in 1 .. max_steps:
    ask the LLM to pick ≤ max_pick ids from skeleton(frontier)
    picked leaves        → evidence
    picked inner nodes   → their children are the next frontier
    stop when nothing is left to open, or at the step limit (then read the whole document)
nothing found?           → BM25 over what is left (still vectorless)
```

*Checkpoint D:* `pytest` shows **64 passed**.

## 5. Part B · Run and compare (about 45 minutes)

### B1 · Watch it think (Lab 1 chat tab → **Vectorless**)

Ask each question in **MQR + RRF** and then in **Vectorless**. For vectorless, read the
**Navigation path** in the inspector.

| # | Question | What to look for |
|---|---|---|
| 1 | `What does PAY-E4035 mean?` | Exact code: does it go straight to `04 → 04.4`? |
| 2 | `Can I WFH on Fridays?` | Vocabulary gap: does "WFH" reach *Hybrid working → Anchor days*? |
| 3 | `deploy on 30th?` | Vague: does it find the *change freeze* (28th–2nd)? |
| 4 | `As a grad trainee, how much learning budget do I get and do I carry the on-call pager?` | Two documents: does it open **both** 10 and 07? |
| 5 | `PAY-E5000 just fired. What process do we follow, and how fast must on-call acknowledge?` | Cross-reference: 04.5 says "follow the Sev-2 process". Does it also open 07? |

### B2 · Same question, four pipelines (Compare tab)

Use questions 2, 4 and 5. For each pipeline, write down the passages sent, whether the answer
is right, the **LLM calls** and the **embedding calls**.

### B3 · Measure (Evaluate tab)

Press **Run evaluation**. Every mode starts with cold caches, so the cost columns are each
mode's own. Fill in:

| Metric | Basic | MQR | MQR + RRF | Vectorless |
|---|---|---|---|---|
| Hit rate | | | | |
| MRR | | | | |
| exact-id / paraphrase / vague / multi-part | | | | |
| Avg context chars | | | | |
| LLM calls / question | | | | |
| Embedding calls / question | | | | |
| Avg retrieval time | | | | |
| One-off index cost | 59 chunks embedded | same | same | 12 LLM calls (cached) |
| BM25 fallbacks | – | – | – | |

Report **per question type**, not just the average. Then look at every ✗ in the Vectorless
column. Was the right document not opened (level 1), or the right section not picked
(level 2)? Hover the cell, then re-ask that question in the chat tab to see the path.

## 6. Part C · Experiments (pick at least two, about 30 minutes)

1. **How much do signposts matter?** In **Tree index**, switch to *Extractive* and then to
   *Titles only*. Re-run Evaluate after each. Plot hit rate against summary mode.
2. **Breadth.** Set `VECTORLESS_MAX_SECTIONS=2`, then `6`. Restart and re-run Evaluate. What
   happens to the hit rate on *multi-part* questions, and to the context size?
3. **Depth.** Set `VECTORLESS_MAX_STEPS=1`: the navigator only picks documents and reads them
   whole. Compare hit rate, context chars and LLM calls.
4. **Resilience.** Set `EMBED_MODEL` to a name that does not exist and restart. Which modes
   still work? Why?
5. **Change the knowledge base.** Upload a new `.md` file on the Knowledge base tab. How many
   LLM calls does the next vectorless question spend on summaries? (Look for the "One-off:
   summaries" line in the inspector.) Why not 13?

## 7. Part D · Discuss (about 15 minutes)

1. Vectorless needs no embedding model and no vector database. What does it pay instead, and
   at which moment (indexing or question time)?
2. Which question types did vectorless win, and which did it lose? Explain each with the
   navigation path.
3. Our handbook is 12 short files (about 14,000 characters in total). For a corpus this small,
   which other option might beat every retriever in this app? When would it stop working?
4. You must serve 50 questions per second with answers in under one second. Which mode do you
   choose, and why?
5. A 400-page regulation with strict audit requirements: which mode, and what would you add?
6. **Is vectorless RAG always better?** Answer with numbers from your table.

## 8. Stretch goals

1. **Hybrid router.** Use BM25 over document titles and signposts to shortlist 3 documents,
   then navigate only inside them (one LLM call fewer). Add it as a fifth mode and measure it.
2. **Follow cross-references.** After reading the picked sections, look for references such
   as "follow the Sev-2 process" and give the navigator one more round. Question 5 is the test.
3. **Sufficiency loop.** Reuse Lab 2's `ASSESS` prompt: if the evidence is not sufficient,
   navigate again with a note of what is missing.
4. **A tool for the agent.** Add a `tree` tool next to `search` and `entity` in
   `app/agent/tools.py`, and let the planner choose it.
5. **Harder evaluation.** Add 5 questions of a new type, `structure` (cross-references,
   "list every …", multi-hop), to `data/eval_set.json`, and re-run all four modes.

## 9. Project map (new in Lab 3)

| File | What it is | Edit? |
|---|---|---|
| `app/vectorless/tree.py` | Tree index, signposts, disk cache, nodes → Documents | **TODO V1, V2** |
| `app/vectorless/navigator.py` | Navigation loop, id validation, BM25 fallback | **TODO V3, V4** |
| `app/vectorless/prompts.py` | `TREE_SUMMARY`, `TREE_NAVIGATE` (JSON replies) | no (stretch: tune) |
| `app/pipeline.py` | `vectorless` mode, `/api/compare`, evaluation with cost per mode | no |
| `app/routes.py` | `GET /api/tree`, `POST /api/tree/summarize` | no |
| `frontend/src/TreeTab.jsx` | Tree index tab: outline, signposts, summary mode switch | no |
| `frontend/src/Inspector.jsx` | Navigation path + nodes seen, for vectorless answers | no |
| `tests/test_vectorless.py` | V01–V14 (fake LLM, offline, free) | no |

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `501 · TODO V1` in Vectorless mode | Expected until V1–V4 are implemented. |
| Every signpost tagged `extractive` after pressing *LLM summaries* | The model did not return JSON. Check the reply with a print in `summarize_document()`. |
| Many `↩` (BM25 fallback) in Evaluate | The navigator reply is not usable JSON, or it invents ids. Check `parse_selection()` and the trace. |
| First vectorless question is slow | It is writing the 12 summaries. Press *LLM summaries* on the Tree index tab before class; the cache makes later restarts free. |
| Summaries out of date after you edit a prompt | Bump `SUMMARY_PROMPT_VERSION` in `prompts.py`, or delete `data/.cache/`. |
