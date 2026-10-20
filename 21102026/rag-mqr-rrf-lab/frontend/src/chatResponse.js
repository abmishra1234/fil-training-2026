// Reject incompatible API responses before they reach the React render path.
export function validateChatResponse(result) {
  const invalid = (field) => {
    const error = new Error(`Cannot display chat response: invalid or missing ${field}.`);
    error.hint = "Restart the backend from this project folder and refresh the page. If it persists, check the /api/chat response in the browser Network tab.";
    throw error;
  };
  if (!result || typeof result !== "object") invalid("response");
  for (const field of ["answer", "mode"]) {
    if (typeof result[field] !== "string") invalid(field);
  }
  for (const field of ["queries", "generated_queries", "sources", "pool"]) {
    if (!Array.isArray(result[field])) invalid(field);
  }
  for (const field of ["queries", "generated_queries"]) {
    if (result[field].some((item) => typeof item !== "string")) invalid(field);
  }
  for (const field of ["chunks_retrieved", "chunks_sent", "context_chars", "approx_prompt_tokens", "llm_calls", "embedding_calls"]) {
    if (!Number.isFinite(result[field])) invalid(field);
  }
  if (!result.timings_ms || !Number.isFinite(result.timings_ms.total)) invalid("timings_ms.total");
  for (const field of ["sources", "pool"]) {
    for (const item of result[field]) {
      if (!item || ["chunk_id", "source", "text"].some((key) => typeof item[key] !== "string")) invalid(`${field} passage`);
      if (item.section != null && typeof item.section !== "string") invalid(`${field}.section`);
      if (field === "pool" && result.mode !== "basic" && !Array.isArray(item.found_by)) invalid("pool.found_by");
    }
  }
  return result;
}
