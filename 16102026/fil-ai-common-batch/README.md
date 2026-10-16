# LLM API samples: FIL enterprise or direct, switched by `.env`

The same Python scripts run **inside Fidelity** (FIL AI Gateway + Azure AD token) or
**outside it** (OpenAI or any OpenAI-compatible API key). You change one line in `.env`:

```
LLM_MODE=enterprise   # students at FIL: client_id + secret + tenant_id + gateway URL
LLM_MODE=direct       # trainer / home: OPENAI_API_KEY (+ optional OPENAI_BASE_URL)
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

## The scripts (in deck order)

| Script | Scenario | API |
|---|---|---|
| `00_check_setup.py` | Token + gateway smoke test | MSAL, chat |
| `01_first_call.py` | First chat call, roles, usage | `chat.completions` |


Run order that needs no extra files: 00 → 01 → 03 → 04 → 05 → copy `output/speech.mp3` into `recordings/` → 06 → 07.
For 08, add two images you have the rights to use as `inputs/product.jpeg` and `inputs/model.jpg`.

## How the switch works

Every script does `client = get_client()` from `llm_client.py` and then uses the standard OpenAI SDK.
Only `llm_client.py` knows about the two modes:

- **enterprise**: MSAL `ConfidentialClientApplication` with
  authority `https://login.microsoftonline.com/<FIL_TENANT_ID>` gets a token for the scope
  (`FIL_ENV=uat` → `https://uat.filxgptnp.fil.com/.default`, `dev` → `https://dev.filxgptnp.fil.com/.default`).
  The token is attached to **every request** through an `httpx.Auth` hook, so it is refreshed
  automatically when it expires (MSAL serves it from cache otherwise). Long jobs like
  folder transcription keep working past the token's one-hour lifetime.
- **direct**: plain `OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or default)`.

Model names (`CHAT_MODEL`, `EMBED_MODEL`, …) live in `.env` because the gateway routes by model name
and may not offer every model the public API has.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Could not get a token from Azure AD: invalid_client` | Wrong client secret, or the secret has expired |
| `AADSTS700016` | Wrong client id or tenant id |
| `401` from the gateway | Token minted for the wrong environment (UAT token on DEV): check `FIL_ENV` and `FIL_BASE_URL` match |
| `403` from the gateway | App registration not granted access to that environment or model: check the SRM ticket |
| `CERTIFICATE_VERIFY_FAILED` | Internal gateway cert: set `CA_BUNDLE` to the corporate CA `.pem` |
| `model not found` / `400` | That model name isn't exposed by the gateway: change `*_MODEL` in `.env` |
| Hangs then times out | Gateway slow or unreachable (VPN?): `LLM_TIMEOUT_SECONDS` stops it hanging forever |

## Rules for students
- Never commit `.env` or paste secrets into notebooks or chat. `.gitignore` already excludes `.env`.
- Inside FIL, use only the enterprise credentials from your SRM ticket, never a personal API key.
