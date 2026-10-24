import React, { useEffect, useRef, useState } from "react";
import { api, streamAgent } from "./api.js";
import { Answer, ErrorBox } from "./ui.jsx";

const newThread = () => (crypto?.randomUUID ? crypto.randomUUID() : `t-${Date.now()}-${Math.random().toString(16).slice(2)}`);

// Layout of the mini graph map (rows). Highlights the nodes this turn visited.
const MAP = [
  ["contextualize", "route"],
  ["direct_answer", "clarify", "plan"],
  ["retrieve", "assess"],
  ["generate", "check", "finalize"],
];
const NODE_INFO = {
  contextualize: "memory: rewrite follow-ups",
  route: "adaptive: direct / clarify / simple / complex",
  direct_answer: "no retrieval",
  clarify: "interrupt: ask the user",
  plan: "decompose into sub-questions",
  retrieve: "tools: search · entity (parallel)",
  assess: "grade + enough? loop",
  generate: "grounded answer + calculator",
  check: "self-check, maybe rewrite",
  finalize: "save to memory",
};
const ROUTE_TONE = { direct: "t-slate", clarify: "t-amber", simple: "t-teal", complex: "t-violet" };

export default function AgentTab({ health }) {
  const [threadId, setThreadId] = useState(newThread);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [awaiting, setAwaiting] = useState(false);
  const [live, setLive] = useState([]);
  const [selected, setSelected] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [compare, setCompare] = useState({});
  const endRef = useRef(null);

  useEffect(() => {
    api.scenarios().then((d) => setScenarios(d.scenarios), () => {});
  }, []);
  useEffect(() => { const el = endRef.current?.parentElement; if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" }); }, [messages, live, busy]);

  function reset() {
    setThreadId(newThread());
    setMessages([]);
    setLive([]);
    setSelected(null);
    setAwaiting(false);
    setCompare({});
  }

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    const id = Date.now();
    setMessages((m) => [...m, { id, role: "user", text: q, resume: awaiting }]);
    setBusy(true);
    setLive([]);
    const body = awaiting ? { resume: q, thread_id: threadId } : { question: q, thread_id: threadId };
    try {
      await streamAgent(body, (ev) => {
        if (ev.type === "step") setLive((l) => [...l, ev]);
        else if (ev.type === "error") setMessages((m) => [...m, { id: id + 1, role: "error", error: { message: ev.detail, hint: ev.hint, status: ev.status } }]);
        else if (ev.type === "final") {
          if (ev.status === "needs_clarification") {
            setAwaiting(true);
            setMessages((m) => [...m, { id: id + 1, role: "clarify", res: ev }]);
          } else {
            setAwaiting(false);
            setMessages((m) => [...m, { id: id + 1, role: "bot", res: ev }]);
          }
          setSelected(ev);
        }
      });
    } catch (e) {
      setMessages((m) => [...m, { id: id + 1, role: "error", error: e }]);
    } finally {
      setBusy(false);
    }
  }

  async function runCompare(msgId, res) {
    setCompare((c) => ({ ...c, [msgId]: { loading: true } }));
    try {
      const r = await api.chat(res.standalone || res.question, "mqr_rrf");
      setCompare((c) => ({ ...c, [msgId]: { res: r } }));
    } catch (e) {
      setCompare((c) => ({ ...c, [msgId]: { error: e } }));
    }
  }

  const steps = busy ? live : selected?.steps ?? [];

  return (
    <div className="chat-layout agent-layout">
      <section className="panel chat-panel">
        <div className="agent-head">
          <div>
            <h2>Agentic RAG</h2>
            <p className="muted small">LangGraph agent: routes, plans, retrieves in parallel, grades, loops, calculates, self-checks and remembers.</p>
          </div>
          <div className="thread-box">
            <span className="chip" title={threadId}>thread {threadId.slice(0, 8)}</span>
            <button className="btn small-btn" onClick={reset} disabled={busy}>New conversation</button>
          </div>
        </div>

        <div className="thread">
          {messages.length === 0 && (
            <div className="empty">
              <h2>Questions Lab 1 struggles with</h2>
              <p>Each scenario shows one weakness of MQR + RRF. Run it here, then press <b>Compare with MQR + RRF</b> under the answer.</p>
              <div className="scenarios">
                {scenarios.map((s) => (
                  <button key={s.id} onClick={() => send(s.question)} title={s.why}>
                    <span className="sc-tag">{s.id} · {s.problem}</span>
                    <span>{s.question}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => {
            if (m.role === "user")
              return (
                <div key={m.id} className="msg user">
                  <div className="bubble">{m.text}</div>
                  {m.resume && <span className="mode-badge m-mqr">clarification</span>}
                </div>
              );
            if (m.role === "error") return <div key={m.id} className="msg bot"><ErrorBox error={m.error} /></div>;
            if (m.role === "clarify")
              return (
                <div key={m.id} className="msg bot" onClick={() => setSelected(m.res)}>
                  <div className="bubble clarify-bubble">
                    <span className="tag gen">needs clarification</span>
                    <p>{m.res.clarify_question}</p>
                    <small className="muted">The graph is paused (interrupt). Your next message resumes it.</small>
                  </div>
                </div>
              );
            const r = m.res;
            const cmp = compare[m.id];
            return (
              <div key={m.id} className={`msg bot ${selected === r ? "selected" : ""}`} onClick={() => setSelected(r)}>
                <div className="bubble">
                  <Answer text={r.answer} />
                  <div className="meta">
                    <span className={`route-chip ${ROUTE_TONE[r.route] || ""}`}>{r.route}</span>
                    <span>{r.llm_calls} LLM calls</span>
                    {r.rounds > 0 && <span>{r.rounds} round{r.rounds > 1 ? "s" : ""}</span>}
                    {r.sources.length > 0 && <span>{r.sources.length} passages</span>}
                    {r.calculations.length > 0 && <span>🧮 {r.calculations.length}</span>}
                    {r.check?.grounded === false && <span className="warn">not grounded</span>}
                    {r.route !== "direct" && (
                      <button className="link-btn" onClick={(e) => (e.stopPropagation(), runCompare(m.id, r))} disabled={cmp?.loading}>
                        {cmp?.loading ? "running…" : "Compare with MQR + RRF"}
                      </button>
                    )}
                  </div>
                </div>
                {cmp?.res && (
                  <div className="compare-card">
                    <div className="cc-head"><span className="mode-badge m-mqr_rrf">Lab 1 · MQR + RRF</span><small>{cmp.res.chunks_sent} chunks · 2 LLM calls · always retrieves</small></div>
                    <Answer text={cmp.res.answer} />
                  </div>
                )}
                {cmp?.error && <ErrorBox error={cmp.error} />}
              </div>
            );
          })}
          {busy && (
            <div className="msg bot"><div className="bubble typing"><i /><i /><i /></div></div>
          )}
          {scenarios.length > 0 && messages.length > 0 && !busy && (
            <div className="samples left">
              {scenarios.filter((s) => s.followup && messages.filter((m) => m.role === "user").slice(-1)[0]?.text === s.question).map((s) => (
                <button key={s.id} onClick={() => send(s.followup)}>Follow-up ({s.id}): {s.followup}</button>
              ))}
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={(e) => (e.preventDefault(), send())}>
          <input value={input} onChange={(e) => setInput(e.target.value)} maxLength={1000} aria-label="Message"
            placeholder={awaiting ? "Answer the clarification question…" : health?.chunks ? "Ask anything about the NovaPay handbook…" : "Index is empty: see Knowledge base"} />
          <button type="submit" disabled={busy || !input.trim()}>{awaiting ? "Reply" : "Ask"}</button>
        </form>
      </section>

      <aside className="panel inspector">
        <div className="insp-head">
          <h3>Agent trace</h3>
          {busy ? <span className="chip good">running…</span> : selected && <span className={`route-chip ${ROUTE_TONE[selected.route] || ""}`}>{selected.route}</span>}
        </div>
        <GraphMap steps={steps} />
        <h4>Steps</h4>
        {steps.length === 0 ? (
          <p className="muted small">Ask something to see every node the graph runs, live.</p>
        ) : (
          <ol className={`timeline ${busy ? "live" : ""}`}>
            {steps.map((s, i) => (
              <li key={i} className={`tl-${s.node}`}>
                <span className="tl-node">{s.node}</span>
                <span className="tl-detail">{s.detail}</span>
                <span className="tl-ms">{s.data?.llm ? "LLM · " : ""}{s.ms} ms</span>
              </li>
            ))}
          </ol>
        )}
        {!busy && selected && <Details r={selected} />}
      </aside>
    </div>
  );
}

function GraphMap({ steps }) {
  const counts = {};
  steps.forEach((s) => (counts[s.node] = (counts[s.node] || 0) + 1));
  return (
    <div className="gmap" aria-label="Graph nodes visited">
      {MAP.map((row, i) => (
        <div key={i} className="gmap-row">
          {row.map((n) => (
            <div key={n} className={`gnode ${counts[n] ? "on" : ""}`} title={NODE_INFO[n]}>
              <b>{n}</b>
              {counts[n] > 1 && <span className="gcount">×{counts[n]}</span>}
              <small>{NODE_INFO[n]}</small>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function Details({ r }) {
  const [open, setOpen] = useState(null);
  return (
    <>
      {r.route_reason && (
        <>
          <h4>Router decision</h4>
          <p className="small"><b>{r.route}</b>: {r.route_reason}</p>
        </>
      )}
      {r.standalone && r.standalone !== r.question && (
        <>
          <h4>Standalone question (memory)</h4>
          <p className="small">{r.standalone}</p>
        </>
      )}
      {r.plan?.length > 0 && (
        <>
          <h4>Plan</h4>
          <ol className="queries">
            {r.plan.map((p) => (
              <li key={p.id}>
                <span className={`tag ${p.tool === "entity" ? "gen" : "orig"}`}>{p.tool}</span>
                {p.tool === "entity" ? <span><b>{p.entity}</b> <span className="muted">({p.question})</span></span> : p.question}
              </li>
            ))}
          </ol>
        </>
      )}
      {r.calculations?.length > 0 && (
        <>
          <h4>Calculator</h4>
          <ul className="calc-list">
            {r.calculations.map((c, i) => <li key={i}><code>{c.expr}</code> = <b>{c.value ?? c.error}</b></li>)}
          </ul>
        </>
      )}
      {r.sources?.length > 0 && (
        <>
          <h4>Passages used ({r.relevant_count} relevant of {r.evidence_count} found)</h4>
          <div className="sources">
            {r.sources.map((s) => (
              <div key={s.chunk_id} className={`source ${open === s.chunk_id ? "open" : ""} ${s.cited ? "cited" : ""}`}>
                <button className="source-head" onClick={() => setOpen(open === s.chunk_id ? null : s.chunk_id)}>
                  <span className="num-badge">{s.n}</span>
                  <span className="src">{s.source}</span>
                  <span className="tag orig">{s.tool} · {s.sub_id}</span>
                  {s.cited && <span className="tag gen">cited</span>}
                </button>
                {open === s.chunk_id && <pre>{s.text}</pre>}
              </div>
            ))}
          </div>
        </>
      )}
      {r.check && Object.keys(r.check).length > 0 && (
        <>
          <h4>Self-check</h4>
          <p className="small">
            {r.check.skipped ? "skipped" : `grounded: ${r.check.grounded ? "yes" : "no"} · complete: ${r.check.complete ? "yes" : "no"}`}
            {r.regenerations > 0 && ` · rewritten ${r.regenerations}×`}
            {r.check.problem && <><br /><em>{r.check.problem}</em></>}
          </p>
        </>
      )}
      <h4>Cost</h4>
      <div className="kv">
        <span>LLM calls</span><b>{r.llm_calls}</b>
        <span>Embedding calls</span><b>{r.embedding_calls ?? "–"}</b>
        <span>Total</span><b>{r.steps.reduce((a, s) => a + (s.ms || 0), 0)} ms</b>
        <span>Turns in thread</span><b>{r.turns}</b>
      </div>
    </>
  );
}
