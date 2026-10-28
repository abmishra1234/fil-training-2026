# Observability: trace LLM calls and application flows in LangSmith

The app talks to the LLM through **one file**, `llm_client.py`. It initializes
OpenTelemetry on first use of `get_client()` and wraps OpenAI chat and embeddings
requests in spans. Inside FIL the spans go through the **FIL AI Observability**
endpoint (`fil-aiobs` SDK); in direct mode they go to LangSmith's OTLP endpoint.

```
 your app ── chat / embeddings ──► FIL AI Gateway  (Azure AD token via MSAL, Step 1)
    │                      └─ traceparent header (gateway spans join your trace)
    └─ OpenTelemetry spans ──► fil-aiobs init_otel ──► FIL AI Observability ──► LangSmith project
                                (Step 2)                /api/v1/otel              (x_api_key = lsv2_...)
```

## 1. Configure (once)

```bash
pip install -r requirements.txt
pip install fil-aiobs                 # FIL internal package index
cp .env.example .env                  # then edit:
```

| Variable | Inside FIL | Outside FIL |
|---|---|---|
| `LLM_MODE` | `enterprise` | `direct` |
| `FIL_CLIENT_ID / FIL_CLIENT_SECRET / FIL_TENANT_ID` | from your SRM ticket | – |
| `OBS_MODE` | `fil` | `otlp` |
| `OBS_ENDPOINT` | UAT: `https://fil-ai-observability-uat.k8s.npiek8sinfra1np1.npaws.ukfilcld/api/v1/otel` | `https://api.smith.langchain.com/otel` |
| `LANGSMITH_API_KEY` | your `lsv2_...` key | same |
| `LANGSMITH_PROJECT` | e.g. `rag-lab-uat-<yourname>` | same |
| `OBS_CAPTURE_CONTENT` | `false` for client / personal data | `true` |
| `LANGSMITH_TRACING` | **`false`** (OpenTelemetry route only) | `false` |

## 2. Verify

```bash
python 00_check_setup.py               # gateway + token
python 01_check_observability.py       # sends a test trace, prints what to look for
python 01_check_observability.py --no-llm   # telemetry only, no gateway calls
pytest tests/test_observability.py     # offline: spans, nesting, traceparent, errors
```

`00_check_setup.py` currently makes a chat request only; it does not make an
embedding request. It also does not create a named workflow/root span. Since it uses
`get_client()`, the chat call should still produce one standalone `chat <model>` span
when observability initializes successfully. `01_check_observability.py` is a stronger
end-to-end check: it explicitly starts the exporter, creates a root span and context
metadata, exercises chat and embeddings, then explicitly flushes. This is why its
LangSmith trace looks more complete and predictable.

### Add tracing to a script

1. Route model access through `llm_client.get_client()`; do not instantiate a raw
   `OpenAI()` client elsewhere. This centrally adds request-level chat and embedding
   spans and initializes the exporter.
2. Add a named root span around the useful unit of work. Nested calls then appear in
   one trace instead of as unrelated top-level spans:

   ```python
   from llm_client import get_client, settings, span, set_output, flush_observability

   client = get_client()
   with span("setup_check", kind="chain", inputs={"check": "connectivity"}) as root:
       reply = client.chat.completions.create(
           model=settings.chat_model,
           messages=[{"role": "user", "content": "Reply with pong"}],
       )
       set_output(root, reply.choices[0].message.content)
   flush_observability()
   ```

3. For application-specific stages (retrieval, prompt building, tools), use
   `@traced(...)` or `with span(...)` around those stages. Add `obs_context(...)` for
   session/user identifiers and tags when traces should group into a LangSmith thread.
4. For short scripts and notebooks, call `flush_observability()` after the final
   span so buffered exports finish before the process exits. The atexit hook is a
   fallback, not a replacement for a deterministic flush in one-off scripts.
5. Verify with `python 01_check_observability.py` and locate the trace in the
   configured project. `--no-llm` checks telemetry plumbing with synthetic spans but
   skips real chat and embedding calls.

## 3. What is traced automatically

| Where | Span | LangSmith run type |
|---|---|---|
| any `client.chat.completions.create` | `chat <model>` (messages, answer, tokens) | llm |
| any `client.embeddings.create` | `embeddings <model>` | embedding |
| FastAPI `/api/*` request | `POST /api/chat` (root of the trace) | chain |
| pipeline steps | `rag.run`, `rag.retrieve`, `mqr.generate_queries`, `rrf.fuse`, `generate_grounded_answer`, `vectorless.tree_search` | chain / retriever |

## 4. Trace your own code

```python
from llm_client import traced, span, set_output, obs_context

@traced("retrieve_docs", kind="retriever")      # kind: chain|llm|retriever|tool|prompt|parser|embedding
def retrieve(q): ...

with obs_context(session_id=thread_id, user_id="u-42", tags=["beta"]):   # -> Threads tab, filters
    answer(q)

with span("build_prompt", kind="prompt", inputs={"q": q}) as sp:
    prompt = ...
    set_output(sp, prompt)
```

Short scripts and notebooks: call `llm_client.flush_observability()` at the end
(it also runs automatically when the process exits).

## 5. Troubleshooting

| You see | Check |
|---|---|
| `[observability] DISABLED - ModuleNotFoundError fil_aiobs` | `pip install fil-aiobs` from the FIL index, or use `OBS_MODE=otlp` outside FIL |
| No trace from an LLM request | use `get_client()` (it initializes and instruments the shared client); check `describe_observability()` for initialization errors |
| LLM run exists but no workflow tree | add a root `span(...)` / `@traced(...)`; request instrumentation alone records only the model call |
| check script OK, nothing in LangSmith | project name; wait 30 s; UAT vs PROD endpoint; LangSmith key belongs to the right workspace |
| flush timed out / SSL errors | VPN, `CA_BUNDLE`, corporate proxy (`HTTPS_PROXY` / `NO_PROXY`) |
| LLM spans have no prompt text | `OBS_CAPTURE_CONTENT=false` (by design) |
| each step is its own trace | the outer function is not `@traced`, or work moved to a thread pool without copying context |
| duplicate traces | `LANGSMITH_TRACING=true` as well; set it to `false` |
