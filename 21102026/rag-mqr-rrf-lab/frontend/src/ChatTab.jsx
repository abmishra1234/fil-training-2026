import React, { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { Answer, ErrorBox, ModeBadge, MODES } from "./ui.jsx";
import Inspector from "./Inspector.jsx";

const SAMPLES = [
  "Can I WFH on Fridays?",
  "What does PAY-E4035 mean?",
  "How do I fix AUTH-E1107?",
  "Someone stole my laptop from the cab. What now?",
  "deploy on 30th?",
  "As a grad trainee, how much learning budget do I get and do I carry the on-call pager?",
];

export default function ChatTab({ health }) {
  const [mode, setMode] = useState("mqr_rrf");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(null);
  const [focusCite, setFocusCite] = useState(null);
  const endRef = useRef(null);
  const nextId = useRef(0);

  useEffect(() => {
    // Some browsers return a Promise here. Effects may only return a cleanup function.
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  async function ask(q) {
    const text = (q ?? question).trim();
    if (!text || busy) return;
    setQuestion("");
    const id = nextId.current;
    nextId.current += 2;
    setMessages((m) => [...m, { id, role: "user", text, mode }]);
    setBusy(true);
    try {
      const res = await api.chat(text, mode);
      setMessages((m) => [...m, { id: id + 1, role: "bot", res }]);
      setSelected(res);
      setFocusCite(null);
    } catch (e) {
      setMessages((m) => [...m, { id: id + 1, role: "error", error: e, mode }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-layout">
      <section className="panel chat-panel">
        <div className="mode-switch" role="radiogroup" aria-label="Retrieval mode">
          {MODES.map((m) => (
            <button key={m.id} role="radio" aria-checked={mode === m.id} className={`seg m-${m.id} ${mode === m.id ? "on" : ""}`} onClick={() => setMode(m.id)}>
              <b>{m.label}</b>
              <small>{m.desc}</small>
            </button>
          ))}
        </div>

        <div className="thread">
          {messages.length === 0 && (
            <div className="empty">
              <h2>Ask the NovaPay handbook</h2>
              <p>Ask the same question in each mode and watch the Retrieval inspector: which chunks were found, and which reached the LLM.</p>
              <div className="samples">
                {SAMPLES.map((s) => (
                  <button key={s} onClick={() => ask(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="msg user">
                <div className="bubble">{m.text}</div>
                <ModeBadge mode={m.mode} />
              </div>
            ) : m.role === "error" ? (
              <div key={m.id} className="msg bot"><ErrorBox error={m.error} /></div>
            ) : (
              <div key={m.id} className={`msg bot ${selected === m.res ? "selected" : ""}`} onClick={() => { setSelected(m.res); setFocusCite(null); }}>
                <div className="bubble">
                  <Answer text={m.res.answer} onCite={(n) => (setSelected(m.res), setFocusCite(n))} />
                  <div className="meta">
                    <ModeBadge mode={m.res.mode} />
                    <span>{m.res.chunks_retrieved} found</span>
                    <span>{m.res.chunks_sent} sent to LLM</span>
                    <span>~{m.res.approx_prompt_tokens} ctx tokens</span>
                    <span>{(m.res.timings_ms.total / 1000).toFixed(1)} s</span>
                  </div>
                </div>
              </div>
            )
          )}
          {busy && (
            <div className="msg bot"><div className="bubble typing"><i /><i /><i /></div></div>
          )}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={(e) => (e.preventDefault(), ask())}>
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={health?.chunks ? "Ask about leave, travel, error codes, releases…" : "Index is empty: see Knowledge base"} maxLength={1000} aria-label="Question" />
          <button type="submit" disabled={busy || !question.trim()}>Ask</button>
        </form>
      </section>

      <Inspector res={selected} focusCite={focusCite} />
    </div>
  );
}
