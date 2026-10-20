import { validateChatResponse } from "./chatResponse.js";

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
  if (body === null) {
    throw new Error("The API returned a non-JSON response. Open the app on port 8000, or run the frontend dev server with the API running on port 8000.");
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
  chat: (question, mode) => request("/api/chat", json("POST", { question, mode })).then(validateChatResponse),
  compare: (question) => request("/api/compare", json("POST", { question })).then((results) => {
    for (const mode of ["basic", "mqr", "mqr_rrf"]) {
      if (!results[mode]?.error) validateChatResponse(results[mode]);
    }
    return results;
  }),
  evaluate: (modes) => request("/api/evaluate", json("POST", { modes })),
};
