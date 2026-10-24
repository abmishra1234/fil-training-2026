import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import { ErrorBox } from "./ui.jsx";

export default function DocumentsTab({ onChange }) {
  const [docs, setDocs] = useState([]);
  const [active, setActive] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [note, setNote] = useState("");

  const load = () => api.documents().then((d) => setDocs(d.documents), setError);
  useEffect(() => {
    load();
  }, []);

  async function open(name) {
    setActive(name);
    try {
      setChunks((await api.chunks(name)).chunks);
    } catch (e) {
      setChunks([]);
      setError(e);
    }
  }

  async function act(fn, msg) {
    setBusy(true);
    setError(null);
    setNote("");
    try {
      const r = await fn();
      setNote(msg(r));
      await load();
      onChange?.();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="docs-layout">
      <section className="panel">
        <div className="docs-head">
          <h2>Knowledge base</h2>
          <div className="row">
            <label className={`btn ${busy ? "disabled" : ""}`}>
              Upload .md / .txt
              <input type="file" accept=".md,.txt" hidden disabled={busy}
                onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) act(() => api.upload(f), (r) => `Saved ${r.saved}. Index now has ${r.chunks} chunks.`); }} />
            </label>
            <button className="btn" disabled={busy} onClick={() => act(api.reindex, (r) => `Re-indexed: ${r.chunks} chunks.`)}>
              {busy ? "Working…" : "Re-index"}
            </button>
          </div>
        </div>
        <p className="muted">Files in <code>data/docs</code>. Each is split by Markdown heading, then to ≤ CHUNK_SIZE characters, embedded with ada-002 and stored in an in-memory FAISS index.</p>
        {note && <p className="ok">{note}</p>}
        <ErrorBox error={error} />
        <ul className="doc-list">
          {docs.map((d) => (
            <li key={d.source} className={active === d.source ? "on" : ""}>
              <button onClick={() => open(d.source)}>
                <span>{d.source}</span>
                <b>{d.chunks} chunks</b>
              </button>
            </li>
          ))}
        </ul>
      </section>
      <section className="panel chunk-view">
        {!active ? (
          <p className="muted">Pick a file to see exactly how it was chunked. Good chunks = good retrieval.</p>
        ) : (
          <>
            <h3>{active}</h3>
            {chunks.map((c) => (
              <div key={c.chunk_id} className="chunk">
                <div className="chunk-id">{c.chunk_id} · {c.text.length} chars</div>
                <pre>{c.text}</pre>
              </div>
            ))}
          </>
        )}
      </section>
    </div>
  );
}
