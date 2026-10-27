import React, { useState } from "react";
import { api } from "./api.js";
import { ErrorBox, fmt, MODES } from "./ui.jsx";

export default function EvaluateTab() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setData(await api.evaluate(MODES.map((m) => m.id)));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const types = data ? [...new Set(data.rows.map((r) => r.type))] : [];

  return (
    <div className="stack">
      <section className="panel eval-intro">
        <div>
          <h2>Measure, don't guess: quality AND cost</h2>
          <p className="muted">
            15 questions from <code>data/eval_set.json</code>. A question is a <b>hit</b> when a chunk that reaches the LLM contains the expected text.
            Retrieval only: no answers are generated. Every mode starts with cold caches, so its LLM calls, embedding calls and latency are its own.
            Cost of one run: about 60 chat calls + 135 embedding calls (+12 chat calls once, if the tree summaries are not written yet).
          </p>
        </div>
        <button className="primary" onClick={run} disabled={busy}>{busy ? "Evaluating…" : "Run evaluation"}</button>
      </section>
      <ErrorBox error={error} />
      {data && (
        <>
          <div className="eval-cards">
            {MODES.map((m) => {
              const s = data.summary[m.id];
              return (
                <section key={m.id} className={`panel eval-card m-${m.id}`}>
                  <h3>{m.label}</h3>
                  {s.status === "todo" ? (
                    <p className="warn">{s.message}</p>
                  ) : (
                    <>
                      <div className="big">{Math.round(s.hit_rate * 100)}<small>% hit rate</small></div>
                      <div className="bar"><i style={{ width: `${s.hit_rate * 100}%` }} /></div>
                      <div className="kv">
                        <span>MRR</span><b>{fmt(s.mrr, 2)}</b>
                        <span>Avg chunks sent</span><b>{s.avg_chunks_sent}</b>
                        <span>Avg context</span><b>{s.avg_context_chars?.toLocaleString()} chars</b>
                        <span>LLM calls / q</span><b>{s.llm_calls_per_q}</b>
                        <span>Embedding calls / q</span><b>{s.embedding_calls_per_q}</b>
                        <span>Avg retrieval time</span><b>{s.avg_ms} ms</b>
                        {m.id === "vectorless" && (<>
                          <span>One-off index calls</span><b>{s.index_llm_calls}</b>
                          <span>BM25 fallbacks</span><b>{s.fallbacks}</b>
                        </>)}
                        {types.map((t) => (
                          <React.Fragment key={t}><span>{t}</span><b>{s.by_type[t] != null ? `${Math.round(s.by_type[t] * 100)}%` : "–"}</b></React.Fragment>
                        ))}
                      </div>
                    </>
                  )}
                </section>
              );
            })}
          </div>
          <section className="panel">
            <table className="eval-table">
              <thead>
                <tr>
                  <th>ID</th><th>Type</th><th>Question</th>
                  {MODES.map((m) => <th key={m.id}>{m.short}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.id}>
                    <td className="mono">{r.id}</td>
                    <td><span className="tag orig">{r.type}</span></td>
                    <td title={`expects: ${r.must_contain}`}>{r.question}</td>
                    {MODES.map((m) => {
                      const c = r[m.id];
                      if (!c) return <td key={m.id} className="na">–</td>;
                      return (
                        <td key={m.id} className={c.hit ? "hit" : "miss"} title={`${c.llm} LLM · ${c.emb} embedding · ${c.ms} ms`}>
                          {c.hit ? `✓ #${c.rank}` : "✗"} <small>/{c.chunks}{c.fallback ? " ↩" : ""}</small>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted small">✓ #n = the expected chunk was at position n of the chunks sent; /m = chunks (vectorless: whole sections) sent to the LLM; ↩ = navigator reply unusable, BM25 fallback. Hover a cell for its cost.</p>
          </section>
        </>
      )}
    </div>
  );
}
