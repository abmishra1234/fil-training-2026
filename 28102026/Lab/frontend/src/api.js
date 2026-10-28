// All HTTP calls in one place. Errors carry the backend's `detail` + `hint`.
async function request(path, options = {}) {
  const res = await fetch(path, options);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* empty or non-JSON body */
  }
  if (!res.ok) {
    let detail = body?.detail ?? res.statusText;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; "); // FastAPI 422
    const err = new Error(detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.hint = body?.hint ?? "";
    throw err;
  }
  return body;
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body ?? {}),
});

export const api = {
  health: () => request("/api/health"),
  documents: () => request("/api/documents"),
  chunks: (name) => request(`/api/documents/${encodeURIComponent(name)}/chunks`),
  upload: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("/api/documents", { method: "POST", body: fd });
  },
  reindex: () => request("/api/reindex", { method: "POST" }),
  chat: (question, mode) => request("/api/chat", json("POST", { question, mode })),
  compare: (question) => request("/api/compare", json("POST", { question })),
  evaluate: (modes) => request("/api/evaluate", json("POST", { modes })),
  // ---- Lab 3: vectorless (tree index) ----
  tree: () => request("/api/tree"),
  summarize: (mode) => request("/api/tree/summarize", json("POST", { mode })),
  // ---- Lab 2: agent ----
  scenarios: () => request("/api/agent/scenarios"),
  agentGraph: () => request("/api/agent/graph"),
  entities: () => request("/api/graph/entities"),
  entity: (name) => request(`/api/graph/entity/${encodeURIComponent(name)}`),
};

// Server-Sent Events over POST: calls onEvent({type: "start"|"step"|"final"|"error", ...})
export async function streamAgent(body, onEvent) {
  const res = await fetch("/api/agent/stream", json("POST", body));
  if (!res.ok) {
    let b = null;
    try { b = await res.json(); } catch { /* ignore */ }
    let detail = b?.detail ?? res.statusText;
    if (Array.isArray(detail)) detail = detail.map((d) => d.msg).join("; ");
    const err = new Error(detail);
    err.status = res.status;
    err.hint = b?.hint ?? "";
    throw err;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
