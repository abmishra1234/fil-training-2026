# Setup · Direct vs Enterprise: one switch, same lab code

Every lab tool talks to the LLM through **one function** (`tools/llm_adapter.py → chat()`),
which uses **one client** (`tools/llm_client.py → get_client()`).
Which LLM you reach is decided by **one line in `.env`**:

```
LLM_MODE=enterprise    # inside FIL: FIL AI Gateway + Azure AD token
LLM_MODE=direct        # at home / trainer laptop: OpenAI-compatible API + API key
LLM_MODE=mock          # offline dry run: no network, no credentials
```

No lab script, skill or test changes when you switch. That is the point.

## 3-minute setup

```bash
pip install -r tools/requirements.txt
cp tools/.env.example .env            # Windows: copy tools\.env.example .env
#   edit .env: set LLM_MODE and fill ONLY the block for that mode
python tools/check_setup.py           # tells you exactly which step is broken
```

`.env` lives in the lab folder (next to `README.md`). Real environment variables, if set,
win over `.env`. `.env` is in `.gitignore`: never commit it.

## What actually changes between the two modes

| | Direct | Enterprise (FIL) |
|---|---|---|
| Who you are | An **API key** (a shared secret) | An **app identity**: client ID + secret in Azure AD (Entra ID) |
| What is sent per request | The same API key, every time | A short-lived **bearer token** (~1 hour), fetched by MSAL and cached |
| Where calls go | `api.openai.com` or `OPENAI_BASE_URL` | `FIL_BASE_URL`, the FIL AI Gateway (UAT or DEV) |
| Token scope | — | `FIL_ENV=uat` or `dev`; a UAT token is rejected by DEV |
| Model names | `DIRECT_CHAT_MODEL`, e.g. `gpt-4o-mini` | `ENTERPRISE_CHAT_MODEL`, e.g. `azure/gpt-6-luna`; the gateway routes by name |
| TLS | Public certificates | May need the corporate CA: `CA_BUNDLE=…pem` |
| Limits and cost | Your own account | Gateway quota per credential (for grad training: 200 requests/min, $50/month) |
| Audit | Provider logs under your key | Gateway logs every call against the team's app identity |

## How the switch is built (worth reading)

* `get_client()` returns a standard `OpenAI` client in both modes, so every caller uses the
  same SDK calls.
* In enterprise mode the client gets an `httpx.Auth` hook that asks MSAL for a token
  **before every request**. MSAL serves it from cache and only goes to Azure AD near expiry,
  so long batch jobs don't fail with 401 after an hour.
* Model names are resolved per mode (`ENTERPRISE_CHAT_MODEL` / `DIRECT_CHAT_MODEL`), so
  changing `LLM_MODE` alone is enough.
* `describe()` and `check_setup.py` print where calls go and the token **length**, never
  the token or secret itself.

## Link to today's topic: this IS primitive 6 (Connector)

The enterprise path is a small connector to a system of record (the gateway):

| Tier 1 idea | In `llm_client.py` |
|---|---|
| Connector with auth | MSAL client-credentials → bearer token on each request |
| Least privilege | Grad credentials can reach exactly two models |
| Credentials never in instructions | Secrets only in `.env` / environment, never in SKILL.md or code |
| Errors teach | `check_setup.py` names the failing step and the fix |

Production skills go one step further: an MCP connector uses **on-behalf-of** token
exchange (RFC 8693), so the system sees the *user*, not a shared app identity.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Missing setting 'FIL_CLIENT_ID'` | You chose enterprise but left that block empty; fill it or use `direct` / `mock` |
| `Could not get a token from Azure AD: invalid_client` | Wrong client secret, or it expired: ask the trainer |
| 401 / 403 from the gateway | `FIL_ENV` does not match the gateway URL (UAT token on DEV, or the reverse) |
| `CERTIFICATE_VERIFY_FAILED` | Set `CA_BUNDLE` to the corporate root CA `.pem` |
| 404 / unknown model | Check `ENTERPRISE_CHAT_MODEL` (enterprise) or `DIRECT_CHAT_MODEL` (direct) |
| Works at home, fails in office | Expected if `.env` still says `direct`: switch the one line |
