# FundLens starter repo

This is a skeleton, not a solution. It gives you the fixed contracts (schemas, API routes, state fields), a working
LLM client (gateway + offline mock), corpus readers, and the evaluation plumbing. Everything marked
`>>> YOU BUILD THIS <<<` is your team's work.

## First 30 minutes

1. Create your team's Git repo from the contents of this `starter/` folder. Then copy the kit's `corpus/`, `data/`, `evaluation/` and `MANIFEST.sha256` into a `kit/` folder inside the repo:

   ```
   your-repo/
     src/ ui/ scripts/ tests/ Makefile requirements.txt ...
     kit/  corpus/ data/ evaluation/ MANIFEST.sha256     <- copied unchanged from the zip
   ```

   This keeps Docker and CI self-contained. (Running the starter in place inside the unzipped kit also works: it falls back to `..`.)
2. `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`)
3. `make setup` (or `pip install -r requirements.txt`)
4. `cp .env.example .env` and fill in the gateway URL/key and LangSmith key.
5. `make check` - must print ALL GOOD. No gateway yet? set `FUNDLENS_LLM_MODE=mock` and carry on.
6. `make test` and `make api`, then open http://localhost:8000/health and http://localhost:8000/docs

## What is already done vs what you build

| Ready to use | You build |
| --- | --- |
| `config.py`, `llm_client.py` (retry, cache, mock), `schemas.py`, `corpus_utils.py`, `agent/state.py`, `/health`, `scripts/*`, `Makefile` | chunker, hybrid retriever (MQR + RRF), tools, compliance check, guardrails, LangGraph graph, review store, remaining API routes, UI, your own tests |

Do not change the public shapes in `schemas.py` (you may add optional fields). The evaluation depends on them.
