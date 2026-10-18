# Classroom assignment: Ad Composer

**Goal:** finish the backend so that a user who uploads a *model image*, a *product image* and a
*marketing quote* gets back a finished **advertisement image**, styled by the settings they chose.

The frontend, FastAPI app shell, `llm_client.py`, `.env` switch, fonts and tests are **already done**.
You implement **8 TODOs** (about 150 lines of Python). Every TODO has a docstring that tells you
exactly what to do, and a test file that tells you when you are done.

## Before you start (10 min)

1. Setup exactly as in `README.md`, then `python 00_check_setup.py` must print `All good`.
2. Set `AD_DRY_RUN=true` in `.env` for now.
3. `uvicorn app.main:app --reload` → open http://127.0.0.1:8000. The page loads, but buttons
   answer **"TODO n: implement …"**. That message tells you which TODO is blocking that button.
4. `pytest` → 46 failing tests. Your job: make them pass.

## The TODOs (do them in this order)

| # | File | Function | What you learn | Tests |
|---|---|---|---|---|
| 1a | `app/prompt_builder.py` | `clean_quote()` | Sanitising user text before it enters a prompt | `test_1_prompt_builder.py` |
| 1b | `app/prompt_builder.py` | `build_ad_prompt()` | **Settings → structured prompt**: sections, image order, text modes, guard-rails | `test_1_prompt_builder.py` |
| 7 | `app/routes.py` | `POST /api/prompt/preview` | Your first FastAPI endpoint with Pydantic models | `test_5_to_8_api.py::test_prompt_preview` |
| 2 | `app/image_service.py` | `normalize_upload()` | Validating uploads with Pillow, HTTP status codes 400/413/415 | `test_2_3_image_service.py` |
| 4a | `app/text_overlay.py` | `wrap_text()` | Pixel-based word wrap | `test_4_text_overlay.py` |
| 4b | `app/text_overlay.py` | `overlay_quote()` | **Text + image composition** with Pillow | `test_4_text_overlay.py` |
| 6 | `app/routes.py` | `POST /api/ads/compose` | Multipart upload endpoint that wires everything | `test_5_to_8_api.py` |
| 3 | `app/image_service.py` | `compose_with_llm()` | **Multi-image edit call** through `get_client()`, timeouts, error mapping | `test_2_3_image_service.py` |
| 5 | `app/quote_service.py` | `refine_quote()` | Chat call that must return machine-readable JSON | `test_5_to_8_api.py` |
| 8 | `app/routes.py` | `POST /api/quote/refine` | Thin endpoint over a service | `test_5_to_8_api.py` |

**Checkpoint A** (after 1a, 1b, 7): "Preview prompt" works in the UI.
**Checkpoint B** (after 2, 4a, 4b, 6): "Generate ad" works in **dry-run** and shows the collage with your quote on it.
**Checkpoint C** (after 3): set `AD_DRY_RUN=false`, generate a real ad with `quality=low`.
**Checkpoint D** (after 5, 8): "✦ Refine with AI" suggests three headlines.

## Rules

- **Do not change** `llm_client.py`, `.env.example`, `schemas.py`, `main.py`, the frontend or the tests.
  If you think one of them is wrong, ask the trainer.
- Every model call goes through `get_client()` from `llm_client.py`. No `OpenAI(...)` anywhere else,
  no hard-coded model names (use `settings.image_model` / `settings.chat_model`).
- Use `quality=low` and `variations=1` while testing real calls: they are slow and they cost money.
- Validate uploads **before** calling the model. A 415 should never cost an image call.

## Done means

- [ ] `pytest` shows **47 passed**
- [ ] One real ad generated with `text_mode=ai`, one with `text_mode=overlay`, same inputs
- [ ] You can explain to your neighbour why `overlay` exists when the model can draw text itself

## Stretch goals (pick any)

1. **Hinglish quotes:** try `"Har din, naya glow"` with `ai` vs `overlay`. Which one spells it right?
2. **Logo slot:** accept an optional third image (brand logo) and add it to `image=[...]`. Update the prompt.
3. **Cost guard:** refuse `quality=high` together with `variations=3` (HTTP 400 with a helpful hint).
4. **A/B prompt:** add `prompt_version` to `AdSettings` and compare two prompt templates side by side.
5. **Async:** turn `/api/ads/compose` into `POST` → job id, plus `GET /api/jobs/{id}` polling, so the browser
   never waits on one long HTTP request.
