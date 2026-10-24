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
          <h2>Measure, don't guess</h2>
          <p className="muted">
            15 questions from <code>data/eval_set.json</code>. A question is a <b>hit</b> when a chunk that reaches the LLM contains the expected text.
            Retrieval only: no answers are generated. Cost: about 15 chat calls + 60 embedding calls.
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
                        <td key={m.id} className={c.hit ? "hit" : "miss"}>
                          {c.hit ? `✓ #${c.rank}` : "✗"} <small>/{c.chunks}</small>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted small">✓ #n = the expected chunk was at position n of the chunks sent; /m = chunks sent to the LLM.</p>
          </section>
        </>
      )}
    </div>
  );
}
