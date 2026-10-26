"""
check_setup.py - run this FIRST. It tells you exactly which step is broken.

    python tools/check_setup.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from llm_client import describe, settings  # noqa: E402

print("Config  :", describe())

if settings.mode == "mock":
    from llm_adapter import chat
    print("Reply   :", chat("SKILL ROUTER\n- demo-skill: Use when the user says ping pong hello", "ping pong hello"))
    print("\nMock mode works (offline). Set LLM_MODE=enterprise or direct in .env for real runs.")
    sys.exit(0)

# Step 1 (enterprise only): can we get a token from Azure AD?
if settings.mode == "enterprise":
    from llm_client import get_access_token
    try:
        token = get_access_token()
    except Exception as e:
        sys.exit(f"Token   : FAILED - {e}\n  -> check FIL_CLIENT_ID / FIL_CLIENT_SECRET / FIL_TENANT_ID / FIL_ENV")
    print(f"Token   : OK ({len(token)} chars)")   # never print any part of a token
else:
    print("Token   : not needed in direct mode (API key used)")

# Step 2: can we reach the gateway / API and get a reply from the configured model?
from llm_client import get_client  # noqa: E402
try:
    reply = get_client().chat.completions.create(
        model=settings.chat_model,
        messages=[{"role": "user", "content": "Reply with the single word: pong"}],
    )
except Exception as e:
    hint = ("  -> CERTIFICATE_VERIFY_FAILED? set CA_BUNDLE in .env\n"
            "  -> 401/403? wrong FIL_ENV for this gateway, or credentials expired\n"
            "  -> 404 model? check ENTERPRISE_CHAT_MODEL / DIRECT_CHAT_MODEL")
    sys.exit(f"Call    : FAILED - {type(e).__name__}: {e}\n{hint}")
print("Model   :", reply.model)
print("Reply   :", reply.choices[0].message.content)
print("Tokens  :", reply.usage.total_tokens if reply.usage else "n/a")
print("\nAll good - you are ready for the labs.")
