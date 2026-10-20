import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import ChatTab from "./ChatTab.jsx";
import CompareTab from "./CompareTab.jsx";
import EvaluateTab from "./EvaluateTab.jsx";
import DocumentsTab from "./DocumentsTab.jsx";

const TABS = [
  { id: "chat", label: "Chat" },
  { id: "compare", label: "Compare modes" },
  { id: "evaluate", label: "Evaluate" },
  { id: "docs", label: "Knowledge base" },
];

export default function App() {
  const [tab, setTab] = useState("chat");
  const [health, setHealth] = useState(null);
  const [healthErr, setHealthErr] = useState(null);

  const refreshHealth = () =>
    api.health().then(
      (h) => (setHealth(h), setHealthErr(null)),
      (e) => setHealthErr(e)
    );
  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="logo">R</span>
          <div>
            <h1>RAG Lab</h1>
            <p>Basic RAG → Multi-Query → Reciprocal Rank Fusion</p>
          </div>
        </div>
        <nav className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.id} role="tab" aria-selected={tab === t.id} className={tab === t.id ? "on" : ""} onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="status">
          {healthErr && <span className="chip bad">API offline</span>}
          {health && (
            <>
              <span className="chip" title="Chat model">{health.chat_model}</span>
              <span className="chip" title="Embedding model">{health.embed_model}</span>
              <span className={`chip ${health.chunks ? "good" : "bad"}`} title={health.index_error || health.vector_db}>
                FAISS · {health.chunks} chunks
              </span>
            </>
          )}
        </div>
      </header>

      {health?.index_error && (
        <div className="banner">
          Index not built: {health.index_error} Fix <code>.env</code>, then use <b>Knowledge base → Re-index</b>.
        </div>
      )}

      <main>
        {tab === "chat" && <ChatTab health={health} />}
        {tab === "compare" && <CompareTab />}
        {tab === "evaluate" && <EvaluateTab />}
        {tab === "docs" && <DocumentsTab onChange={refreshHealth} />}
      </main>
    </div>
  );
}
