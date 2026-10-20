# RAG Lab: Basic RAG → Multi-Query Retriever (MQR) → Reciprocal Rank Fusion (RRF)

FIL Graduate AI Cohort · full-stack GenAI lab (FastAPI + LangChain + FAISS + React).

A chatbot answers questions about **NovaPay**, a fictional fintech's handbook
(HR, travel, payments error codes, on-call, releases). **Basic RAG already works.**
Your job: make retrieval *and* generation better with **MQR** and **RRF**, and
**prove** it with numbers.

It uses the same `llm_client.py` and `.env` switch as the earlier samples, so it
runs **inside FIL** (AI Gateway + Azure AD token) or **outside** (OpenAI key) with
the same code:

```
LLM_MODE=enterprise   # at FIL: FIL_CLIENT_ID / FIL_CLIENT_SECRET / FIL_TENANT_ID + gateway URL
LLM_MODE=direct       # trainer / home: OPENAI_API_KEY (+ optional OPENAI_BASE_URL)
```

Models (Grad-training gateway access): `azure/gpt-6-luna` (chat) and
`azure/text-embedding-ada-002` (embeddings).
Direct OpenAI defaults: `gpt-4o-mini` (chat) and `text-embedding-3-small`
(embeddings). Configure `DIRECT_CHAT_MODEL` / `DIRECT_EMBED_MODEL` separately
from `ENTERPRISE_CHAT_MODEL` / `ENTERPRISE_EMBED_MODEL`; switching `LLM_MODE`
then selects the matching pair. Legacy `CHAT_MODEL` / `EMBED_MODEL` remain
fallback overrides. Public OpenAI model IDs must not use the `azure/` prefix.
Each credential has a **$50/month budget** and a **200 requests/minute** limit:
use the cheap paths first (pytest, Compare on a few questions) and run the full
Evaluation once or twice, not in a loop.

## How it works

```
 React (frontend/)                 FastAPI (app/)                                         FIL AI Gateway
 ─────────────────                 ──────────────                                         ──────────────
 Chat / Compare  ── POST /api/chat ──► pipeline.run(mode)
                                       │
   mode=basic    ──────────────────────┼─► basic_rag: FAISS top-5 ─► naive prompt ───────► gpt-6-luna
                                       │
   mode=mqr      ──────────────────────┼─► mqr: LLM writes 3 queries ─────────────────────► gpt-6-luna
                                       │        4 x FAISS top-5 ─► union (~10-18 chunks)    ada-002 (query vectors)
                                       │        ─► grounded prompt (ALL chunks) ─────────► gpt-6-luna
                                       │
   mode=mqr_rrf  ──────────────────────┴─► mqr union ─► semantic rank + BM25 rank
                                                     ─► RRF ─► top-5 ─► grounded prompt ─► gpt-6-luna

 Evaluate tab    ── POST /api/evaluate ─► retrieval-only hit-rate / MRR per mode (data/eval_set.json)
 Knowledge base  ── /api/documents, /api/reindex ─► data/docs/*.md ─► chunks ─► ada-002 ─► FAISS (in memory)
```

## Setup (10 minutes)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
# edit .env -> set LLM_MODE and fill in that block only
python 00_check_setup.py      # tells you which step is broken, if any
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** (the app, pre-built React) or **http://127.0.0.1:8000/docs** (Swagger).

On startup the server chunks `data/docs`, embeds every chunk with ada-002 (1 request)
and builds an in-memory FAISS index. Restarting rebuilds it.

### Changing the frontend (optional)

The React source is in `frontend/src`. A built copy is already in `frontend/dist`,
so you do **not** need Node.js to do the lab. To change the UI:

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (calls the API on :8000)
npm run build      # updates frontend/dist, served by FastAPI
```

## Test

```bash
pytest             # 25 tests, fake gateway: free, offline, < 2 seconds
pytest -k rrf      # just the RRF tests
pytest -x          # stop at the first failure
```

## Project map

| File | What it is | You edit? |
|---|---|---|
| `llm_client.py`, `00_check_setup.py` | shared gateway client and setup check (same as earlier labs) | no |
| `app/llm.py` | `GatewayEmbeddings` (LangChain Embeddings) + `chat_complete()` | no |
| `app/ingest.py` | Markdown-aware chunking with LangChain text splitters | no |
| `app/vector_store.py` | in-memory **FAISS** (Meta) vector DB | no |
| `app/basic_rag.py` | **Basic RAG** as a LangChain LCEL chain (the "before") | no |
| `app/mqr.py` | Multi-Query Retriever | **TODO 1-4** |
| `app/rerank.py` | BM25, semantic re-rank, RRF | **TODO 5-8** |
| `app/generation.py` | grounded, cited answer generation | **TODO 9-10** |
| `app/pipeline.py`, `routes.py`, `main.py`, `schemas.py` | service, API, evaluation | no |
| `data/docs/*.md` | knowledge base (fictional) | add your own in stretch goals |
| `data/eval_set.json` | 15 questions with the expected evidence | stretch goals |
| `tests/` | 25 edge-case tests | no |
| `frontend/` | React + Vite UI (`dist/` is pre-built) | optional |

The exercise handout (`RAG_MQR_RRF_Exercise.docx`) explains every TODO, the rules,
checkpoints and stretch goals.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Banner "Index not built" | `.env` is wrong. Run `python 00_check_setup.py`, then *Knowledge base → Re-index*. |
| `401/403` | Wrong client id/secret, or `FIL_ENV` does not match the gateway URL (UAT vs DEV). |
| `400 invalid model ID` / `404 model not found` | Check the selected mode's model overrides. Enterprise uses `azure/gpt-6-luna` / `azure/text-embedding-ada-002`; direct OpenAI uses `gpt-4o-mini` / `text-embedding-3-small`. |
| `429` | 200 req/min or the $50 monthly budget. Wait a minute; don't loop Evaluate. |
| `CERTIFICATE_VERIFY_FAILED` | Set `CA_BUNDLE` in `.env` to the corporate root CA `.pem`. |
| "Mode 'mqr' is not ready yet" (HTTP 501) | Expected until you implement the TODOs. Basic mode works from minute one. |
