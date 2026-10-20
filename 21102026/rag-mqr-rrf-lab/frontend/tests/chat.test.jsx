import React from "react";
import { act, create } from "react-test-renderer";
import assert from "node:assert/strict";
import test from "node:test";
import ChatTab from "../src/ChatTab.jsx";
import ErrorBoundary from "../src/ErrorBoundary.jsx";
import { existsSync, readFileSync } from "node:fs";

const response = (mode) => ({
  mode, question: "Can I WFH on Fridays?", answer: "**Yes**, with approval [1].",
  queries: ["Can I WFH on Fridays?"], generated_queries: [],
  sources: [{ chunk_id: "policy.md#0", source: "policy.md", section: "Remote work", text: "With approval", cited: true }],
  pool: [{ chunk_id: "policy.md#0", source: "policy.md", text: "With approval", section: "Remote work", found_by: ["Can I WFH on Fridays?"], semantic_rank: 1, bm25_rank: 1, rrf_score: 0.032 }],
  chunks_retrieved: 1, chunks_sent: 1, context_chars: 13, approx_prompt_tokens: 4,
  llm_calls: 2, embedding_calls: 1, timings_ms: { total: 20 },
});

for (const mode of ["basic", "mqr", "mqr_rrf"]) {
  test(`chat renders a ${mode} query response and citation`, async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({ ok: true, json: async () => response(mode) });
    let view;
    try {
      await act(async () => {
        view = create(<ChatTab health={{ chunks: 1 }} />, {
          createNodeMock: () => ({ scrollIntoView() { return Promise.resolve(); } }),
        });
      });
      await act(async () => {
        view.root.findAllByProps({ role: "radio" }).find((b) => b.props.className.includes(`m-${mode} `)).props.onClick();
      });
      await act(async () => {
        view.root.findAllByType("button").find((b) => b.children.includes("Can I WFH on Fridays?")).props.onClick();
      });
      assert.match(JSON.stringify(view.toJSON()), /Remote work/);
      const cite = view.root.findByProps({ className: "cite" });
      await act(async () => cite.props.onClick({ stopPropagation() {} }));
      assert.match(JSON.stringify(view.toJSON()), /With approval/);
    } finally {
      await act(async () => view?.unmount());
      globalThis.fetch = originalFetch;
    }
  });
}

test("a render failure shows its error and can be reset", async () => {
  let fail = true;
  function Child() {
    if (fail) throw new Error("Response render failed");
    return <p>Recovered</p>;
  }
  const originalError = console.error;
  console.error = () => {};
  let view;
  try {
    await act(async () => { view = create(<ErrorBoundary><Child /></ErrorBoundary>); });
    assert.equal(view.root.findByProps({ role: "alert" }).type, "div");
    assert.match(JSON.stringify(view.toJSON()), /Response render failed/);
    fail = false;
    await act(async () => view.root.findByType("button").props.onClick());
    assert.match(JSON.stringify(view.toJSON()), /Recovered/);
  } finally {
    await act(async () => view?.unmount());
    console.error = originalError;
  }
});

test("an incompatible query response shows an error and permits another query", async () => {
  const originalFetch = globalThis.fetch;
  let result = { answer: "An incompatible response" };
  globalThis.fetch = async () => ({ ok: true, json: async () => result });
  let view;
  try {
    await act(async () => {
      view = create(<ChatTab health={{ chunks: 1 }} />, { createNodeMock: () => ({ scrollIntoView() { return Promise.resolve(); } }) });
    });
    await act(async () => view.root.findAllByType("button").find((b) => b.children.includes("Can I WFH on Fridays?")).props.onClick());
    assert.match(JSON.stringify(view.toJSON()), /Cannot display chat response/);
    result = response("mqr_rrf");
    await act(async () => view.root.findByType("input").props.onChange({ target: { value: "Try again" } }));
    await act(async () => view.root.findByType("form").props.onSubmit({ preventDefault() {} }));
    assert.match(JSON.stringify(view.toJSON()), /Remote work/);
  } finally {
    await act(async () => view?.unmount());
    globalThis.fetch = originalFetch;
  }
});

if (existsSync("node_modules/.cache/live-chat.json")) {
  test("the locally captured live API response renders after submitting a query", async () => {
    const originalFetch = globalThis.fetch;
    const result = JSON.parse(readFileSync("node_modules/.cache/live-chat.json", "utf8"));
    globalThis.fetch = async () => ({ ok: true, json: async () => result });
    let view;
    try {
      await act(async () => {
        view = create(<ChatTab health={{ chunks: 59 }} />, { createNodeMock: () => ({ scrollIntoView() { return Promise.resolve(); } }) });
      });
      await act(async () => view.root.findAllByType("button").find((b) => b.children.includes("Can I WFH on Fridays?")).props.onClick());
      assert.equal(view.root.findAllByProps({ className: "error-box" }).length, 0);
      assert.equal(view.root.findAllByProps({ className: "answer" }).length, 1);
    } finally {
      await act(async () => view?.unmount());
      globalThis.fetch = originalFetch;
    }
  });
}
