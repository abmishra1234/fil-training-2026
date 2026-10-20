import React, { useState } from "react";
import { api } from "./api.js";
import { Answer, ErrorBox, MODES } from "./ui.jsx";

const SAMPLES = ["Can I WFH on Fridays?", "PAY-E4035 keeps coming in prod, any idea?", "login blocked after wrong password"];

export default function CompareTab() {
  const [question, setQuestion] = useState("");
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run(q) {
    const text = (q ?? question).trim();
    if (!text) return;
    setQuestion(text);
    setBusy(true);
    setError(null);
    setData(null);
    try {
      setData(await api.compare(text));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <section className="panel">
        <h2>Same question, three pipelines</h2>
        <p className="muted">Runs Basic RAG, MQR and MQR + RRF one after another. MQR rewrites are cached, so MQR + RRF reuses them.</p>
        <form className="composer inline" onSubmit={(e) => (e.preventDefault(), run())}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Type a question…" aria-label="Question" />
          <button disabled={busy || !question.trim()}>{busy ? "Running…" : "Compare"}</button>
        </form>
        <div className="samples left">
          {SAMPLES.map((s) => <button key={s} onClick={() => run(s)}>{s}</button>)}
        </div>
      </section>
      <ErrorBox error={error} />
      {busy && <div className="panel loading">Running 3 pipelines…</div>}
      {data && (
        <div className="compare-grid">
          {MODES.map((m) => {
            const r = data[m.id];
            return (
              <section key={m.id} className={`panel cmp m-${m.id}`}>
                <header>
                  <h3>{m.label}</h3>
                  <small>{m.desc}</small>
                </header>
                {r?.error ? (
                  <ErrorBox error={{ message: r.error, hint: r.hint, status: r.status }} />
                ) : (
                  <>
                    <div className="cmp-stats">
                      <div><b>{r.chunks_retrieved}</b><span>found</span></div>
                      <div><b>{r.chunks_sent}</b><span>sent</span></div>
                      <div><b>~{r.approx_prompt_tokens}</b><span>ctx tokens</span></div>
                      <div><b>{(r.timings_ms.total / 1000).toFixed(1)}s</b><span>latency</span></div>
                    </div>
                    <Answer text={r.answer} />
                    <h4>Passages sent</h4>
                    <ol className="mini-sources">
                      {r.sources.map((s) => (
                        <li key={s.chunk_id} className={s.cited ? "cited" : ""}>
                          <span>{s.source.replace(/\.(md|txt)$/, "")}</span>
                          <em>{s.section}</em>
                        </li>
                      ))}
                    </ol>
                  </>
                )}
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
