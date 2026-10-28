import React, { useEffect, useState } from "react";
import { api } from "./api.js";
import ChatTab from "./ChatTab.jsx";
import CompareTab from "./CompareTab.jsx";
import EvaluateTab from "./EvaluateTab.jsx";
import DocumentsTab from "./DocumentsTab.jsx";
import AgentTab from "./AgentTab.jsx";
import TreeTab from "./TreeTab.jsx";

const TABS = [
  { id: "agent", label: "Agentic RAG" },
  { id: "chat", label: "Lab 1 chat" },
  { id: "compare", label: "Compare" },
  { id: "evaluate", label: "Evaluate" },
  { id: "tree", label: "Tree index" },
  { id: "docs", label: "Knowledge base" },
];

export default function App() {
  const [tab, setTab] = useState("agent");
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
            <p>Basic RAG → MQR → RRF → Agentic RAG → Vectorless RAG</p>
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
              {health.tree && (
                <span className={`chip ${health.tree.status === "ok" ? "tree" : "bad"}`} title={health.tree.error || `summaries: ${health.tree.summaries}`}>
                  Tree · {health.tree.status === "ok" ? `${health.tree.documents} docs · ${health.tree.leaves} sections` : "TODO V1"}
                </span>
              )}
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
        {tab === "agent" && <AgentTab health={health} />}
        {tab === "chat" && <ChatTab health={health} />}
        {tab === "compare" && <CompareTab />}
        {tab === "evaluate" && <EvaluateTab />}
        {tab === "tree" && <TreeTab onChange={refreshHealth} />}
        {tab === "docs" && <DocumentsTab onChange={refreshHealth} />}
      </main>
    </div>
  );
}
