"""
00_check_setup.py - run this FIRST. It tells you exactly which step is broken.

    python 00_check_setup.py
"""
from llm_client import describe, get_access_token, get_client, settings

print("Config  :", describe())

# Step 1 (enterprise only): can we get a token from Azure AD?
if settings.mode == "enterprise":
    token = get_access_token()
    print(f"Token   : OK ({len(token)} chars, starts {token[:12]}...)")
else:
    print("Token   : not needed in direct mode (API key used)")

# Step 2: can we reach the gateway / API and get a reply?
client = get_client()
reply = client.chat.completions.create(
    model=settings.chat_model,
    messages=[{"role": "user", "content": "Reply with the single word: pong"}],
)
print("Model   :", reply.model)
print("Reply   :", reply.choices[0].message.content)
print("Tokens  :", reply.usage.total_tokens if reply.usage else "n/a")
print("\nAll good - you are ready for the labs.")

