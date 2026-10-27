import React, { useEffect, useState } from "react";
import { fmt, ModeBadge } from "./ui.jsx";

export default function Inspector({ res, focusCite }) {
  const [open, setOpen] = useState(null);
  useEffect(() => {
    if (focusCite && res?.sources?.[focusCite - 1]) setOpen(res.sources[focusCite - 1].chunk_id);
  }, [focusCite, res]);

  if (!res)
    return (
      <aside className="panel inspector empty-insp">
        <h3>Retrieval inspector</h3>
        <p>Ask something. Here you will see the queries that were searched, every chunk that was found, how it ranked, and which chunks were sent to the LLM.</p>
      </aside>
    );

  if (res.mode === "vectorless") return <TreeInspector res={res} open={open} setOpen={setOpen} />;

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

// ---------------------------------------------------------------- Lab 3
function Sources({ res, open, setOpen }) {
  return (
    <div className="sources">
      {res.sources.map((s, i) => (
        <div key={s.chunk_id} className={`source ${open === s.chunk_id ? "open" : ""} ${s.cited ? "cited" : ""}`}>
          <button className="source-head" onClick={() => setOpen(open === s.chunk_id ? null : s.chunk_id)}>
            <span className="num-badge">{i + 1}</span>
            <span className="src">{s.chunk_id}</span>
            {s.cited && <span className="tag gen">cited</span>}
          </button>
          {open === s.chunk_id && <pre>{s.text}</pre>}
        </div>
      ))}
    </div>
  );
}

function TreeInspector({ res, open, setOpen }) {
  const docsSeen = res.pool.filter((r) => r.level === 1).length;
  const opened = res.pool.filter((r) => r.level === 1 && r.picked).length;
  return (
    <aside className="panel inspector">
      <div className="insp-head">
        <h3>Retrieval inspector</h3>
        <ModeBadge mode={res.mode} />
      </div>

      <div className="funnel">
        <div><b>{docsSeen}</b><span>docs seen</span></div>
        <div className="arrow">→</div>
        <div><b>{opened}</b><span>opened</span></div>
        <div className="arrow">→</div>
        <div><b>{res.chunks_retrieved}</b><span>nodes picked</span></div>
        <div className="arrow">→</div>
        <div className="hl tree-hl"><b>{res.chunks_sent}</b><span>sent to LLM</span></div>
        <div className="cut tree-cut">0 embeddings</div>
      </div>

      <h4>Navigation path <span className="legend">the path is the explanation</span></h4>
      <ol className="navpath">
        {res.tree_path.map((st, i) => (
          <li key={i} className={st.fallback ? "fb" : st.ok ? "" : "bad"}>
            <div className="np-head">
              <span className="np-level">{st.fallback ? "fallback" : `level ${st.level}`}</span>
              <span className="np-meta">{st.fallback ? "BM25 · no LLM" : `saw ${st.shown} · LLM · ${st.ms} ms`}</span>
            </div>
            {st.thinking && <p className="np-think">“{st.thinking}”</p>}
            {!st.ok && <p className="warn">Reply unusable (no JSON or only invented ids).</p>}
            <div className="np-picks">
              {st.picked.map((p) => (
                <span key={p.node_id} className={`np-pick ${p.kind}`}><b>{p.node_id}</b> {p.title}</span>
              ))}
            </div>
          </li>
        ))}
      </ol>
      {res.fallback && <p className="warn">The navigator reply could not be used, so BM25 keyword search picked the sections (still vectorless).</p>}

      <h4>
        Nodes the navigator saw
        <span className="legend"><i className="dot tree" /> picked</span>
      </h4>
      <div className="pool">
        <table>
          <thead>
            <tr><th>Node</th><th title="Tree level shown at">Lvl</th><th>Signpost (summary) the LLM read</th></tr>
          </thead>
          <tbody>
            {res.pool.map((r) => (
              <tr key={r.chunk_id} className={r.picked ? "picked" : ""} onClick={() => setOpen(open === r.chunk_id ? null : r.chunk_id)}>
                <td>
                  <span className="cid">{r.node_id}</span>
                  <span className="sec">{r.title}</span>
                </td>
                <td className="num">{r.level}</td>
                <td className="sig">{r.text || <em className="muted">titles only</em>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h4>Passages sent to the LLM (whole sections)</h4>
      <Sources res={res} open={open} setOpen={setOpen} />

      <h4>Cost &amp; latency</h4>
      <div className="kv">
        <span>LLM calls</span><b>{res.llm_calls} ({res.tree_path.filter((s) => !s.fallback).length} navigate + {res.llm_calls - res.tree_path.filter((s) => !s.fallback).length} answer)</b>
        <span>Embedding calls</span><b>{res.embedding_calls}</b>
        {res.index_llm_calls > 0 && (<><span>One-off: summaries</span><b>{res.index_llm_calls} LLM calls</b></>)}
        <span>Summaries</span><b>{res.tree_summaries}</b>
        <span>Context sent</span><b>{res.context_chars.toLocaleString()} chars (~{res.approx_prompt_tokens} tokens)</b>
        {Object.entries(res.timings_ms).map(([k, v]) => (
          <React.Fragment key={k}><span>{k}</span><b>{v} ms</b></React.Fragment>
        ))}
      </div>
    </aside>
  );
}
