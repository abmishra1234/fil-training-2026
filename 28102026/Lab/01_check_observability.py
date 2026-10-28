"""
01_check_observability.py - prove that your LLM app is observable in LangSmith.

Run it AFTER 00_check_setup.py works:

    python 01_check_observability.py             # full test: gateway + traces
    python 01_check_observability.py --no-llm    # telemetry pipeline only (no gateway calls, no cost)
    python 01_check_observability.py --console   # also print every span locally

It sends ONE trace called "obs_smoke_test" with this tree:

    obs_smoke_test                      chain     (root, carries run_id / session_id metadata)
    |- chat azure/gpt-6-luna            llm       "Reply with pong"  -> tokens + cost
    |- embeddings ...ada-002            embedding 2 inputs
    |- mini_rag                         chain
    |  |- retrieve_docs                 retriever 2 documents
    |  |- build_prompt                  prompt
    |  `- chat azure/gpt-6-luna         llm       grounded answer
    `- create_ticket                    tool      ERROR on purpose (KeyError 'priority')

plus a second trace "obs_smoke_test_turn2" with the same session_id (-> LangSmith Threads tab).
Then it prints exactly what to look for in LangSmith.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--no-llm", action="store_true", help="do not call the gateway; test telemetry only")
parser.add_argument("--console", action="store_true", help="also print spans to the console")
args = parser.parse_args()
if args.console:
    os.environ["OBS_CONSOLE_EXPORT"] = "true"  # read by llm_client at import time

import llm_client  # noqa: E402  (loads .env)
from llm_client import (  # noqa: E402
    current_trace_id, describe, describe_observability, flush_observability, get_client,
    init_observability, obs_context, observability_status, set_output, settings, span, traced,
)

OK, FIX = "  OK  ", "  FIX "
problems = 0


def check(ok: bool, good: str, bad: str) -> bool:
    global problems
    print((OK + good) if ok else (FIX + bad))
    problems += 0 if ok else 1
    return ok


print("=" * 72)
print(" LangSmith observability check")
print("=" * 72)
print("LLM     :", describe())

# ---- Step 1: configuration ------------------------------------------------- #
s = observability_status()
print("\n[1] Configuration")
check(s["mode"] in ("fil", "otlp"), f"OBS_MODE={s['mode']}",
      f"OBS_MODE={s['mode']!r} - set OBS_MODE=fil (inside FIL) or otlp (outside) in .env")
check(s["api_key_set"] and "****" not in (llm_client.obs_settings.api_key or ""),
      "LANGSMITH_API_KEY is set", "LANGSMITH_API_KEY is empty or still the placeholder lsv2_sk_****")
check(bool(s["project"]) and s["project"] != "default", f"LANGSMITH_PROJECT={s['project']}",
      "LANGSMITH_PROJECT not set - traces would land in 'default'")
check(bool(s["endpoint"]), f"OBS_ENDPOINT={s['endpoint']}", "OBS_ENDPOINT is empty")
if os.getenv("LANGSMITH_TRACING", "").lower() == "true":
    check(False, "", "LANGSMITH_TRACING=true - turn native tracing off; FIL uses the OpenTelemetry route")
if s["mode"] == "fil":
    try:
        import fil_aiobs  # noqa: F401
        check(True, "fil-aiobs SDK importable", "")
    except ImportError:
        check(False, "", "fil-aiobs not installed: pip install fil-aiobs (FIL internal package index)")

# ---- Step 2: token (enterprise only) ---------------------------------------- #
print("\n[2] Gateway token")
if args.no_llm:
    print("  --  skipped (--no-llm)")
elif settings.mode == "enterprise":
    try:
        tok = llm_client.get_access_token()
        check(True, f"Azure AD token OK ({len(tok)} chars)", "")
    except Exception as err:  # noqa: BLE001
        check(False, "", f"token failed: {err}  -> check FIL_CLIENT_ID / FIL_CLIENT_SECRET / FIL_TENANT_ID / FIL_ENV")
else:
    print("  --  not needed in direct mode")

# ---- Step 3: start OpenTelemetry -------------------------------------------- #
print("\n[3] OpenTelemetry")
active = init_observability()
print("  ", describe_observability())
if not check(active, "tracer provider started", "observability did not start (reason above)"):
    print("\nFix the FIX lines and run again.")
    sys.exit(1)


# ---- Step 4: send the test trace -------------------------------------------- #
DOCS = [
    {"page_content": "Passwords expire every 90 days. You get a reminder 7 days before.",
     "metadata": {"source": "08_security_passwords.md"}},
    {"page_content": "Use the self-service portal to reset a forgotten password.",
     "metadata": {"source": "08_security_passwords.md"}},
]


@traced("retrieve_docs", kind="retriever")
def retrieve_docs(question: str) -> list[dict]:
    time.sleep(0.05)  # pretend to search
    return DOCS


@traced("create_ticket", kind="tool")
def create_ticket(payload: dict) -> str:
    return f"TICKET-{payload['priority']}"  # KeyError on purpose -> a red span in LangSmith


def llm(messages: list[dict]) -> str:
    if args.no_llm:
        with span("chat (skipped: --no-llm)", kind="llm", inputs={"messages": messages}) as sp:
            set_output(sp, "pong")
        return "pong"
    reply = get_client().chat.completions.create(model=settings.chat_model, messages=messages)
    return (reply.choices[0].message.content or "").strip()


@traced("mini_rag")
def mini_rag(question: str) -> str:
    docs = retrieve_docs(question)
    with span("build_prompt", kind="prompt", inputs={"question": question, "docs": len(docs)}) as sp:
        context = "\n".join(f"[{i + 1}] {d['page_content']}" for i, d in enumerate(docs))
        messages = [
            {"role": "system", "content": "Answer only from the context. Cite like [1]."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ]
        set_output(sp, messages)
    return llm(messages)


run_id = uuid.uuid4().hex[:8]
session_id = f"obs-check-{run_id}"
print(f"\n[4] Sending test traces  (run_id={run_id}, session_id={session_id})")

trace_ids = []
with obs_context(session_id=session_id, run_id=run_id, check="01_check_observability", tags=["obs-check"]):
    with span("obs_smoke_test", kind="chain", inputs={"run_id": run_id}) as root:
        trace_ids.append(current_trace_id())
        try:
            pong = llm([{"role": "user", "content": "Reply with the single word: pong"}])
            check("pong" in pong.lower(), f"chat call OK (reply: {pong[:40]!r})", f"unexpected reply {pong[:60]!r}")
        except Exception as err:  # noqa: BLE001
            check(False, "", f"chat call failed: {err}  -> run python 00_check_setup.py first")

        if not args.no_llm:
            try:
                emb = get_client().embeddings.create(model=settings.embed_model, input=["hello", "world"])
                check(len(emb.data) == 2, f"embeddings call OK ({len(emb.data[0].embedding)} dims)", "embeddings returned wrong count")
            except Exception as err:  # noqa: BLE001
                check(False, "", f"embeddings call failed: {err}")

        try:
            answer = mini_rag("When do passwords expire?")
            check(bool(answer), f"mini RAG OK (answer: {answer[:50]!r})", "mini RAG returned nothing")
        except Exception as err:  # noqa: BLE001
            check(False, "", f"mini RAG failed: {err}")

        try:
            create_ticket({"summary": "laptop broken"})
        except KeyError:
            print(f"{OK}planted tool error raised and recorded (KeyError 'priority')")
        set_output(root, {"status": "done", "run_id": run_id})

    with span("obs_smoke_test_turn2", kind="chain", inputs={"question": "And how do I reset it?"}) as sp2:
        trace_ids.append(current_trace_id())
        set_output(sp2, mini_rag("And how do I reset it?"))

# ---- Step 5: flush --------------------------------------------------------- #
print("\n[5] Flush")
check(flush_observability(15_000), "spans exported (flush returned OK)",
      "flush timed out - check network / OBS_ENDPOINT / proxy and CA_BUNDLE")

print("\n" + "=" * 72)
if problems:
    print(f" {problems} problem(s) - fix the FIX lines above and run again.")
else:
    print(" Telemetry sent. Now verify in LangSmith (wait ~10-30 s):")
print("=" * 72)
print(f"""
 1. Open LangSmith -> Tracing -> project  {llm_client.obs_settings.project}
 2. Find the root run  obs_smoke_test   (filter: has(tags, "obs-check")
    or metadata run_id = {run_id})
 3. Expand the tree: chat / embeddings / mini_rag -> retrieve_docs, build_prompt, chat / create_ticket
 4. Click the llm run: messages, model, token counts{" (skipped: --no-llm)" if args.no_llm else ""}
 5. create_ticket is red: open it to see KeyError 'priority' and the exact input that caused it
 6. Threads tab: session {session_id} holds 2 traces
 OpenTelemetry trace ids: {", ".join(t or "-" for t in trace_ids)}
""")
sys.exit(1 if problems else 0)
