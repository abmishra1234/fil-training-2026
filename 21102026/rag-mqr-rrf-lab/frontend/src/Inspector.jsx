import React, { useEffect, useState } from "react";
import { fmt, ModeBadge } from "./ui.jsx";

export default function Inspector({ res, focusCite }) {
  const [open, setOpen] = useState(null);
  useEffect(() => {
    setOpen(focusCite && res?.sources?.[focusCite - 1] ? res.sources[focusCite - 1].chunk_id : null);
  }, [focusCite, res]);

  if (!res)
    return (
      <aside className="panel inspector empty-insp">
        <h3>Retrieval inspector</h3>
        <p>Ask something. Here you will see the queries that were searched, every chunk that was found, how it ranked, and which chunks were sent to the LLM.</p>
      </aside>
    );

  const isRrf = res.mode === "mqr_rrf";
  const sentIds = new Set(res.sources.map((s) => s.chunk_id));
  const reduction = res.chunks_retrieved ? Math.round((1 - res.chunks_sent / res.chunks_retrieved) * 100) : 0;

  return (
    <aside className="panel inspector">
      <div className="insp-head">
        <h3>Retrieval inspector</h3>
        <ModeBadge mode={res.mode} />
      </div>

      <div className="funnel">
        <div><b>{res.queries.length}</b><span>{res.queries.length === 1 ? "query" : "queries"}</span></div>
        <div className="arrow">→</div>
        <div><b>{res.chunks_retrieved}</b><span>chunks found</span></div>
        <div className="arrow">→</div>
        <div className="hl"><b>{res.chunks_sent}</b><span>sent to LLM</span></div>
        {isRrf && reduction > 0 && <div className="cut">−{reduction}%</div>}
      </div>

      <h4>Queries searched</h4>
      <ol className="queries">
        {res.queries.map((q) => (
          <li key={q}>
            <span className={`tag ${res.generated_queries.includes(q) ? "gen" : "orig"}`}>
              {res.generated_queries.includes(q) ? "LLM" : "you"}
            </span>
            {q}
          </li>
        ))}
      </ol>
      {res.llm_failed && <p className="warn">Query generation failed or returned nothing: fell back to your question only.</p>}

      <h4>
        Chunk pool {isRrf ? "(sorted by RRF)" : ""}
        <span className="legend"><i className="dot sent" /> sent to LLM</span>
      </h4>
      <div className="pool">
        <table>
          <thead>
            <tr>
              <th>Chunk</th>
              {res.mode !== "basic" && <th title="How many queries found this chunk">Found by</th>}
              {isRrf && <th title="Rank by cosine similarity">Sem.</th>}
              {isRrf && <th title="Rank by BM25 keywords">BM25</th>}
              {isRrf ? <th title="Reciprocal Rank Fusion score">RRF</th> : <th>Cosine</th>}
            </tr>
          </thead>
          <tbody>
            {res.pool.map((r) => (
              <tr key={r.chunk_id} className={sentIds.has(r.chunk_id) ? "sent" : ""} onClick={() => setOpen(open === r.chunk_id ? null : r.chunk_id)}>
                <td>
                  <span className="cid">{r.source.replace(/\.(md|txt)$/, "")}</span>
                  <span className="sec">{r.section || "—"}</span>
                </td>
                {res.mode !== "basic" && <td className="num">{r.found_by.length}/{res.queries.length}</td>}
                {isRrf && <td className="num">#{r.semantic_rank}</td>}
                {isRrf && <td className="num">#{r.bm25_rank}</td>}
                {isRrf ? <td className="num">{r.rrf_score != null ? fmt(r.rrf_score, 4) : "–"}</td> : <td className="num">{fmt(r.score)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h4>Passages sent to the LLM</h4>
      <div className="sources">
        {res.sources.map((s, i) => (
          <div key={s.chunk_id} className={`source ${open === s.chunk_id ? "open" : ""} ${s.cited ? "cited" : ""}`}>
            <button className="source-head" onClick={() => setOpen(open === s.chunk_id ? null : s.chunk_id)}>
              <span className="num-badge">{i + 1}</span>
              <span className="src">{s.source}</span>
              {s.cited && <span className="tag gen">cited</span>}
            </button>
            {open === s.chunk_id && <pre>{s.text}</pre>}
          </div>
        ))}
      </div>

      <h4>Cost &amp; latency</h4>
      <div className="kv">
        <span>LLM calls</span><b>{res.llm_calls}</b>
        <span>Embedding calls</span><b>{res.embedding_calls}</b>
        <span>Context sent</span><b>{res.context_chars.toLocaleString()} chars (~{res.approx_prompt_tokens} tokens)</b>
        {Object.entries(res.timings_ms).map(([k, v]) => (
          <React.Fragment key={k}><span>{k}</span><b>{v} ms</b></React.Fragment>
        ))}
      </div>
    </aside>
  );
}
