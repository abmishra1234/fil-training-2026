import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { ErrorBox } from "./ui.jsx";

const SUMMARY_MODES = [
  { id: "llm", label: "LLM summaries", desc: "1 call per document, cached on disk" },
  { id: "extractive", label: "Extractive", desc: "first sentence / section list · free" },
  { id: "none", label: "Titles only", desc: "the navigator sees headings only" },
];

const SRC_TONE = { llm: "gen", cache: "gen", extractive: "orig" };

export default function TreeTab({ onChange }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [open, setOpen] = useState({});
  const [leaf, setLeaf] = useState(null);

  const load = () => api.tree().then((d) => (setData(d), setError(null)), setError);
  useEffect(() => {
    load();
  }, []);

  async function summarize(mode) {
    setBusy(true);
    setError(null);
    setNote("");
    try {
      const d = await api.summarize(mode);
      setData(d);
      setNote(d.llm_calls ? `Wrote summaries with ${d.llm_calls} LLM calls (cached for next time).` : `Summaries: ${d.summaries} (0 LLM calls).`);
      onChange?.();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  const docs = data?.tree?.children ?? [];
  const allOpen = docs.length > 0 && docs.every((d) => open[d.node_id]);

  return (
    <div className="docs-layout tree-layout">
      <section className="panel tree-panel">
        <div className="docs-head">
          <h2>Tree index</h2>
          {data && <span className="chip tree">{data.documents} docs · {data.leaves} leaves · summaries: {data.summaries}</span>}
        </div>
        <p className="muted">
          The vectorless index is the handbook's own table of contents: one node per file (<code>#</code>), one per section (<code>##</code>).
          At question time the LLM reads only these ids, titles and signposts, picks where to go, and only then reads the full text of the leaves it chose.
        </p>
        <div className="summary-modes" role="radiogroup" aria-label="Summary mode">
          {SUMMARY_MODES.map((m) => (
            <button key={m.id} role="radio" aria-checked={data?.summary_mode === m.id} disabled={busy}
              className={`seg m-vectorless ${data?.summary_mode === m.id ? "on" : ""}`} onClick={() => summarize(m.id)}>
              <b>{m.label}</b>
              <small>{m.desc}</small>
            </button>
          ))}
        </div>
        <p className="muted small">Switch, then re-run <b>Evaluate</b>: how much do the signposts matter for retrieval quality?</p>
        {busy && <p className="muted">Writing summaries…</p>}
        {note && <p className="ok">{note}</p>}
        <ErrorBox error={error} />
        {docs.length > 0 && (
          <button className="link-btn" onClick={() => setOpen(allOpen ? {} : Object.fromEntries(docs.map((d) => [d.node_id, true])))}>
            {allOpen ? "Collapse all" : "Expand all"}
          </button>
        )}
        <ul className="tree">
          {docs.map((d) => (
            <li key={d.node_id} className="tree-doc">
              <button className="tree-row" onClick={() => (d.children.length ? setOpen({ ...open, [d.node_id]: !open[d.node_id] }) : setLeaf(d))}>
                <span className="tree-caret">{d.children.length ? (open[d.node_id] ? "▾" : "▸") : "•"}</span>
                <span className="tree-id">{d.node_id}</span>
                <span className="tree-title">{d.title}</span>
                <span className="tree-count">{d.children.length ? `${d.children.length} sections` : "single page"}</span>
              </button>
              <Signpost node={d} />
              {open[d.node_id] && (
                <ul>
                  {d.children.map((s) => (
                    <li key={s.node_id} className={leaf?.node_id === s.node_id ? "on" : ""}>
                      <button className="tree-row" onClick={() => setLeaf(s)}>
                        <span className="tree-id">{s.node_id}</span>
                        <span className="tree-title">{s.title}</span>
                        <span className="tree-count">{s.chars} chars</span>
                      </button>
                      <Signpost node={s} />
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </section>
      <section className="panel chunk-view">
        {!leaf ? (
          <p className="muted">Pick a section to see the full text the LLM receives when the navigator chooses it. Compare it with the 500-character chunks on the Knowledge base tab.</p>
        ) : (
          <>
            <h3><span className="tree-id">{leaf.node_id}</span> {leaf.title}</h3>
            <div className="chunk">
              <div className="chunk-id">{leaf.source}::{leaf.node_id} · {leaf.chars} chars</div>
              <pre>{leaf.text}</pre>
            </div>
            <h4 className="muted small">Signpost</h4>
            <p>{leaf.summary || <em className="muted">none (titles only)</em>}</p>
          </>
        )}
      </section>
    </div>
  );
}

function Signpost({ node }) {
  if (!node.summary) return null;
  return (
    <p className="signpost">
      {node.summary_source && <span className={`tag ${SRC_TONE[node.summary_source] || "orig"}`}>{node.summary_source}</span>} {node.summary}
    </p>
  );
}
