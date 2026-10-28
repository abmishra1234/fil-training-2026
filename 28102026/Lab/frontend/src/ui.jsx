import React from "react";

export const MODES = [
  { id: "basic", label: "Basic RAG", short: "Basic", desc: "FAISS top-5 → naive prompt" },
  { id: "mqr", label: "MQR", short: "MQR", desc: "3 rewrites + original → union of all chunks" },
  { id: "mqr_rrf", label: "MQR + RRF", short: "MQR+RRF", desc: "union → semantic + BM25 → RRF top-5" },
  { id: "vectorless", label: "Vectorless", short: "Vectorless", desc: "LLM navigates the tree index · no embeddings" },
];
export const modeLabel = (id) => MODES.find((m) => m.id === id)?.label ?? id;

export function ModeBadge({ mode }) {
  return <span className={`mode-badge m-${mode}`}>{modeLabel(mode)}</span>;
}

// Tiny, safe renderer: paragraphs, "- " bullets, **bold**, and [1] / [1, 2] citation chips.
function inline(text, onCite, keyBase) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[\s*\d+(?:\s*,\s*\d+)*\s*\])/g);
  return parts.map((p, i) => {
    const key = `${keyBase}-${i}`;
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={key}>{p.slice(2, -2)}</strong>;
    const m = p.match(/^\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]$/);
    if (m)
      return m[1].split(",").map((n) => (
        <button key={`${key}-${n}`} className="cite" onClick={() => onCite?.(Number(n))} title={`Passage ${n.trim()}`}>
          {n.trim()}
        </button>
      ));
    return <React.Fragment key={key}>{p}</React.Fragment>;
  });
}

export function Answer({ text, onCite }) {
  const blocks = [];
  let list = null;
  (text || "").split("\n").forEach((raw, i) => {
    const line = raw.trim();
    const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      if (!list) {
        list = [];
        blocks.push({ type: "ul", items: list, key: `ul${i}` });
      }
      list.push(bullet[1]);
    } else {
      list = null;
      if (line) blocks.push({ type: "p", text: line, key: `p${i}` });
    }
  });
  return (
    <div className="answer">
      {blocks.map((b) =>
        b.type === "ul" ? (
          <ul key={b.key}>
            {b.items.map((it, j) => (
              <li key={j}>{inline(it, onCite, `${b.key}-${j}`)}</li>
            ))}
          </ul>
        ) : (
          <p key={b.key}>{inline(b.text, onCite, b.key)}</p>
        )
      )}
    </div>
  );
}

export function Stat({ label, value, tone }) {
  return (
    <div className={`stat ${tone ?? ""}`}>
      <span className="stat-v">{value}</span>
      <span className="stat-l">{label}</span>
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="error-box">
      <strong>{error.status === 501 ? "Not implemented yet" : "Something went wrong"}</strong>
      <span>{error.message}</span>
      {error.hint && <em>{error.hint}</em>}
    </div>
  );
}

export const fmt = (v, d = 3) => (v === null || v === undefined ? "–" : Number(v).toFixed(d));
