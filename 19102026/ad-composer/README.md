# Ad Composer: model + product + quote → advertisement image

FIL AI Cohort · full-stack GenAI lab (FastAPI + plain JS frontend + image model).

The user uploads **a model photo**, **a product photo** and types **a marketing quote**,
picks a few output settings, and the app returns a **finished advertisement image**.

It uses the same `llm_client.py` and `.env` switch as the sample scripts (`00`–`08`),
so it runs **inside FIL** (AI Gateway + Azure AD token) or **outside** (OpenAI key)
with the same code. Change one line in `.env`:

```
LLM_MODE=enterprise   # students at FIL: client_id + secret + tenant_id + gateway URL
LLM_MODE=direct       # trainer / home: OPENAI_API_KEY (+ optional OPENAI_BASE_URL)
```

## How it works

```
 Browser (frontend/)                      FastAPI (app/)                                   LLM gateway / API
 ───────────────────                      ─────────────                                    ─────────────────
 model.jpg  ┐                             routes.compose_ad
 product.jpg├─ multipart POST ─────────►  ├─ parse_settings()      settings JSON → AdSettings
 quote      │  /api/ads/compose           ├─ normalize_upload() x2  validate → PNG bytes
 settings ──┘                             ├─ build_ad_prompt()      settings → ONE prompt
                                          ├─ compose_with_llm() ───────────────────────────►  images.edit(IMAGE_MODEL,
                                          │                         ◄─────────── b64 PNGs ──   image=[model, product])
                                          ├─ overlay_quote()        (text_mode=overlay) Pillow writes the quote
                                          └─ save_images()          output/ad_<id>_<n>.png + ad_<id>.json
 <img src=/api/ads/files/...> ◄── JSON ───┘

 "✦ Refine with AI"  ── POST /api/quote/refine ──► refine_quote() ──► chat.completions(CHAT_MODEL)
 "Preview prompt"    ── POST /api/prompt/preview ─► build_ad_prompt()   (no model call, free)
```

## Setup (5 minutes)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
# edit .env -> set LLM_MODE and fill in that block only
python 00_check_setup.py      # tells you which step is broken, if any
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open **http://127.0.0.1:8000** (the app) or **http://127.0.0.1:8000/docs** (Swagger: try every endpoint by hand).

> **Tip: start with `AD_DRY_RUN=true`** in `.env`. The app then builds a local Pillow collage
> instead of calling the image model, so you can develop and debug the whole flow for free and
> in under a second. Switch to `false` when everything works.

## Tests

```bash
pytest                         # all tests, never calls the real gateway (the client is faked)
pytest tests/test_1_prompt_builder.py -v      # one TODO at a time
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Mode, gateway, model names, dry-run flag |
| GET | `/api/options` | Allowed values for every setting (the frontend builds its controls from this) |
| POST | `/api/prompt/preview` | JSON `{quote, settings}` → the exact prompt, size, text mode. No model call |
| POST | `/api/quote/refine` | JSON `{quote, mood, brand_name}` → 3 headline suggestions from `CHAT_MODEL` |
| POST | `/api/ads/compose` | multipart `model_image`, `product_image`, `quote`, `settings` (JSON string) → ad |
| GET | `/api/ads` | Recent ads (history strip) |
| GET | `/api/ads/files/{name}` | Download one generated PNG |

Errors are always JSON: `{"error": "...", "hint": "..."}`, and the frontend shows both.

## Output settings → prompt

| Setting | Values | Goes to |
|---|---|---|
| style | studio, luxury, minimal, vibrant, festive, lifestyle | prompt SCENE |
| scene | auto, plain-studio, nature-outdoor, urban-street, beach, festive-lights, home-interior | prompt SCENE |
| mood | premium, playful, bold, calm, warm | prompt SCENE (lighting) |
| aspect_ratio | square, landscape, portrait | API `size` 1024x1024 / 1536x1024 / 1024x1536 + prompt LAYOUT |
| quality | low, medium, high | API `quality` (low is fastest and cheapest, good for class) |
| text_mode | ai, overlay, none | prompt TEXT, plus Pillow overlay when `overlay` |
| quote_position | top, center, bottom | prompt LAYOUT/TEXT + overlay band |
| font_style | modern-sans, elegant-serif, bold-display | prompt TEXT + overlay font |
| text_color, accent_color | `#RRGGBB` | prompt TEXT/BRAND + overlay colours |
| brand_name | optional, ≤ 40 chars | prompt BRAND + overlay sub-line |
| variations | 1–3 | API `n` |
| extra_instructions | optional, ≤ 300 chars | prompt, LAST, labelled as lower priority than the rules |

## Project layout

```
llm_client.py          SAME as the samples - the only file that knows enterprise vs direct
00_check_setup.py      SAME as the samples - run first
.env.example           samples' settings + 4 app settings at the bottom
app/
  main.py              FastAPI app, error handlers, serves frontend/
  config.py            app settings (timeout, dry-run, upload limit, input fidelity)
  schemas.py           AdSettings and request/response models (the API contract)
  prompt_builder.py    settings → prompt
  image_service.py     upload validation, image model call, dry-run collage, saving
  text_overlay.py      Pillow text composition (overlay mode)
  quote_service.py     chat model: polish the quote
  routes.py            the HTTP endpoints
  fonts/               DejaVu fonts (free licence), same rendering on Windows/Mac/Linux
frontend/              index.html, styles.css, app.js (no build step)
tests/                 pytest suite with a fake LLM client
inputs/                sample model.jpg and product.jpeg
output/                generated ads (git-ignored)
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Could not get a token from Azure AD: invalid_client` | Wrong client secret, or the secret has expired |
| `AADSTS700016` | Wrong client id or tenant id |
| `401` from the gateway | Token minted for the wrong environment (UAT token on DEV): check `FIL_ENV` and `FIL_BASE_URL` match |
| `403` from the gateway | App registration not granted access to that environment or model: check the SRM ticket |
| `CERTIFICATE_VERIFY_FAILED` | Internal gateway cert: set `CA_BUNDLE` to the corporate CA `.pem` |
| `model not found` / `400` | That model name isn't exposed by the gateway: change `IMAGE_MODEL` / `CHAT_MODEL` in `.env` |
| `400 ... unknown parameter input_fidelity` | Gateway doesn't support it: leave `IMAGE_INPUT_FIDELITY` empty |
| `400 ... safety system` | The image or quote was blocked by content moderation: use other images or wording |
| `504` from the app | Image model slower than `IMAGE_TIMEOUT_SECONDS`: use quality `low` or raise the timeout |
| `501 TODO n` in the UI | That TODO is not implemented yet (starter code) |
| `ModuleNotFoundError: llm_client` | Run `uvicorn` / `pytest` from the project folder, not from `app/` |

## Rules for students
- Never commit `.env` or paste secrets into notebooks or chat. `.gitignore` already excludes `.env`.
- Inside FIL, use only the enterprise credentials from your SRM ticket, never a personal API key.
- Only upload images you have the rights to use. Do not upload photos of colleagues without their consent.
