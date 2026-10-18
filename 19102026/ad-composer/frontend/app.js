/* Ad Composer frontend (PROVIDED - no TODOs here).
 * Plain JavaScript, no build step. Talks to the FastAPI backend on the same origin:
 *   GET  /api/health        GET /api/options      GET /api/ads
 *   POST /api/prompt/preview (JSON)
 *   POST /api/quote/refine   (JSON)
 *   POST /api/ads/compose    (multipart: model_image, product_image, quote, settings=<JSON string>)
 */
const $ = (sel) => document.querySelector(sel);
const state = { files: { model_image: null, product_image: null }, settings: {}, options: null, busy: false };

const TEXT_MODE_HELP = {
  ai: "The image model paints the quote into the picture. Most natural look; spelling can occasionally slip.",
  overlay: "The model leaves a clean band and the server writes the quote with Pillow. Pixel-perfect text.",
  none: "Image only, no headline.",
};

// ---------------------------------------------------------------- helpers
async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw new Error("Cannot reach the backend. Is uvicorn running?");
  }
  const isJson = (res.headers.get("content-type") || "").includes("application/json");
  const body = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    if (body && body.error) msg = body.error + (body.hint ? `\n→ ${body.hint}` : "");
    else if (body && Array.isArray(body.detail)) msg = body.detail.map((d) => `${(d.loc || []).join(".")}: ${d.msg}`).join("\n");
    else if (body && body.detail) msg = String(body.detail);
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return body;
}

function showError(msg) {
  const el = $("#error");
  el.textContent = msg || "";
  el.hidden = !msg;
}

const LABELS = { ai: "AI text", overlay: "Overlay (Pillow)", none: "No text" };
function label(v) { return LABELS[v] || String(v).replace(/-/g, " "); }

// ---------------------------------------------------------------- uploads
function setupDrop(el) {
  const input = el.querySelector("input");
  const img = el.querySelector("img");
  const empty = el.querySelector(".drop-empty");
  const clear = el.querySelector(".clear");
  const field = el.dataset.field;

  const setFile = (file) => {
    if (file && !/^image\/(jpeg|png|webp)$/.test(file.type)) {
      showError("Please choose a JPG, PNG or WEBP image.");
      return;
    }
    state.files[field] = file || null;
    if (file) {
      img.src = URL.createObjectURL(file);
      img.hidden = false; empty.hidden = true; clear.hidden = false;
    } else {
      img.removeAttribute("src");
      img.hidden = true; empty.hidden = false; clear.hidden = true; input.value = "";
    }
  };
  input.addEventListener("change", () => setFile(input.files[0]));
  clear.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); setFile(null); });
  ["dragenter", "dragover"].forEach((t) => el.addEventListener(t, (e) => { e.preventDefault(); el.classList.add("over"); }));
  ["dragleave", "drop"].forEach((t) => el.addEventListener(t, (e) => { e.preventDefault(); el.classList.remove("over"); }));
  el.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));
}

// ---------------------------------------------------------------- settings
function buildChips(container, key, values) {
  container.innerHTML = "";
  values.forEach((v) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "chip"; b.textContent = label(v); b.dataset.value = v;
    b.addEventListener("click", () => { state.settings[key] = v; syncUI(); });
    container.appendChild(b);
  });
}

function syncUI() {
  document.querySelectorAll(".chips").forEach((c) => {
    const key = c.dataset.key;
    c.querySelectorAll(".chip").forEach((b) => b.classList.toggle("on", b.dataset.value === state.settings[key]));
  });
  $("#scene").value = state.settings.scene;
  ["text_color", "accent_color"].forEach((k) => ($("#" + k).value = state.settings[k]));
  $("#variations").value = state.settings.variations;
  $("#variationsOut").textContent = state.settings.variations;
  const tm = state.settings.text_mode;
  $("#textModeHelp").textContent = TEXT_MODE_HELP[tm] || "";
  document.querySelectorAll(".text-only").forEach((el) => el.classList.toggle("disabled", tm === "none"));
}

function collectSettings() {
  const s = { ...state.settings };
  s.brand_name = $("#brand_name").value.trim() || null;
  s.extra_instructions = $("#extra_instructions").value.trim() || null;
  s.variations = Number($("#variations").value);
  return s;
}

async function loadOptions() {
  const opt = await api("/api/options");
  state.options = opt;
  state.settings = { ...opt.defaults };
  document.querySelectorAll(".chips").forEach((c) => buildChips(c, c.dataset.key, opt[c.dataset.key]));
  const sel = $("#scene");
  sel.innerHTML = opt.scene.map((v) => `<option value="${v}">${label(v)}</option>`).join("");
  sel.addEventListener("change", () => (state.settings.scene = sel.value));
  ["text_color", "accent_color"].forEach((k) => $("#" + k).addEventListener("input", (e) => (state.settings[k] = e.target.value.toUpperCase())));
  $("#variations").addEventListener("input", (e) => { state.settings.variations = Number(e.target.value); $("#variationsOut").textContent = e.target.value; });
  $("#quote").maxLength = opt.max_quote_chars;
  syncUI();
}

async function loadHealth() {
  const el = $("#status");
  try {
    const h = await api("/api/health");
    el.className = "status " + (h.dry_run ? "dry" : "ok");
    $("#statusText").textContent = h.dry_run ? `DRY-RUN (no LLM) · ${h.image_model}` : `${h.llm.split(" ")[0]} · ${h.image_model}`;
    el.title = h.llm;
  } catch (e) {
    el.className = "status down";
    $("#statusText").textContent = "Backend offline";
  }
}

// ---------------------------------------------------------------- quote
function updateCount() { $("#quoteCount").textContent = `${$("#quote").value.length} / ${$("#quote").maxLength}`; }

async function refineQuote() {
  const quote = $("#quote").value.trim();
  if (!quote) return showError("Type a quote first, then refine it.");
  showError("");
  const btn = $("#btnRefine");
  btn.disabled = true; btn.textContent = "Thinking…";
  try {
    const r = await api("/api/quote/refine", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quote, mood: state.settings.mood, brand_name: $("#brand_name").value.trim() || null }),
    });
    const box = $("#suggestions");
    box.innerHTML = "";
    r.suggestions.forEach((s) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = s;
      b.addEventListener("click", () => { $("#quote").value = s; updateCount(); box.hidden = true; });
      box.appendChild(b);
    });
    box.hidden = r.suggestions.length === 0;
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false; btn.textContent = "✦ Refine with AI";
  }
}

// ---------------------------------------------------------------- prompt preview
async function previewPrompt(open = true) {
  try {
    const r = await api("/api/prompt/preview", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quote: $("#quote").value, settings: collectSettings() }),
    });
    $("#promptText").textContent = r.prompt;
    if (open) $("#promptBox").open = true;
    showError("");
  } catch (e) {
    showError(e.message);
  }
}

// ---------------------------------------------------------------- generate
function setView(view) {
  $("#placeholder").hidden = view !== "placeholder";
  $("#loading").hidden = view !== "loading";
  $("#results").hidden = view !== "results";
}

async function generate() {
  if (state.busy) return;
  showError("");
  const s = collectSettings();
  const quote = $("#quote").value.trim();
  if (!state.files.model_image || !state.files.product_image) return showError("Please upload both the model image and the product image.");
  if (!quote && s.text_mode !== "none") return showError("Please enter a marketing quote (or choose text mode 'none').");

  const fd = new FormData();
  fd.append("model_image", state.files.model_image);
  fd.append("product_image", state.files.product_image);
  fd.append("quote", quote);
  fd.append("settings", JSON.stringify(s));

  state.busy = true;
  $("#btnGenerate").disabled = true;
  setView("loading");
  const t0 = Date.now();
  const hints = ["Sending images and prompt to the image model", "The model is composing the scene", "Rendering lighting and details", "Almost there - large images take a while"];
  const timer = setInterval(() => {
    const sec = Math.round((Date.now() - t0) / 1000);
    $("#elapsed").textContent = sec + "s";
    $("#loadingHint").textContent = hints[Math.min(hints.length - 1, Math.floor(sec / 20))];
  }, 500);

  try {
    const r = await api("/api/ads/compose", { method: "POST", body: fd });
    renderResult(r);
    loadHistory();
  } catch (e) {
    setView("placeholder");
    showError(e.message);
  } finally {
    clearInterval(timer);
    state.busy = false;
    $("#btnGenerate").disabled = false;
  }
}

function renderResult(r) {
  const box = $("#results");
  box.innerHTML = "";
  r.images.forEach((im, i) => {
    const card = document.createElement("div");
    card.className = "result-card";
    card.innerHTML = `<img src="${im.url}?t=${Date.now()}" alt="Generated advertisement ${i + 1}">
      <div class="bar"><span>Variation ${i + 1}</span><a href="${im.url}" download="${im.filename}">Download PNG</a></div>`;
    card.querySelector("img").addEventListener("click", () => window.open(im.url, "_blank"));
    box.appendChild(card);
  });
  setView("results");
  const meta = $("#meta");
  meta.innerHTML = [
    r.mode === "dry-run" ? "DRY-RUN" : "LLM", r.model, r.settings.aspect_ratio, r.settings.quality + " quality",
    "text: " + r.settings.text_mode, r.elapsed_seconds + "s",
  ].map((t) => `<span>${t}</span>`).join("");
  meta.hidden = false;
  $("#promptText").textContent = r.prompt;
}

async function loadHistory() {
  try {
    const items = await api("/api/ads?limit=12");
    const strip = $("#history");
    if (!items.length) { strip.innerHTML = "<small>No ads yet.</small>"; return; }
    strip.innerHTML = "";
    items.forEach((ad) => {
      const img = document.createElement("img");
      img.src = ad.images[0].url; img.alt = ad.quote; img.title = ad.quote;
      img.addEventListener("click", () => renderResult(ad));
      strip.appendChild(img);
    });
  } catch (_) { /* history is optional - ignore while TODOs are open */ }
}

// ---------------------------------------------------------------- boot
document.addEventListener("DOMContentLoaded", async () => {
  setupDrop($("#dropModel"));
  setupDrop($("#dropProduct"));
  $("#quote").addEventListener("input", updateCount);
  $("#btnRefine").addEventListener("click", refineQuote);
  $("#btnPreview").addEventListener("click", () => previewPrompt(true));
  $("#btnGenerate").addEventListener("click", generate);
  updateCount();
  await loadHealth();
  try { await loadOptions(); } catch (e) { showError(e.message); }
  loadHistory();
});
