
# secure_verify_jwt — README

> Beginner-friendly step-by-step guide to understand, run, and improve `secure_verify_jwt.py`.

This README documents the code in `secure_verify_jwt.py` and provides clear steps for a beginner developer to run it, test it, and improve its security. The original file used for this README is `secure_verify_jwt.py`. 

---

## Table of contents

1. Overview
2. What is a JSON Web Token (JWT)?
3. Files included
4. Quick start — run locally (Windows / macOS / Linux)
5. Deep dive: `secure_verify_jwt.py` explained
6. Environment variables and securing secrets
7. Common runtime errors and troubleshooting
8. Recommended security improvements & checklist
9. Unit testing example (pytest)
10. Simple Jenkins pipeline example
11. Next steps / further reading

---

## 1) Overview

`secure_verify_jwt.py` is a very small demonstration that:
- Creates (encodes) a JWT with a few standard claims (role, iat, exp, iss, aud).
- Verifies (decodes) the JWT, validating the signature and certain claims.

This is a learning/demo file — **not production-ready** as-is. Use this README to learn, then apply the security recommendations below to harden it.

---

## 2) What is a JSON Web Token (JWT)?

A JWT is a compact, URL-safe token used to carry claims between two parties. Typical usage:
- Authentication: after login, server issues a JWT to the client that the client uses on subsequent requests.
- Authorization: tokens carry roles/permissions so services can enforce access control.

A JWT has three parts:
1. Header — algorithm and token type
2. Payload — claims (e.g. `sub`, `iat`, `exp`, `iss`, `aud`, custom claims)
3. Signature — cryptographic signature to prevent tampering

Important claims in the demo:
- `iat` (Issued At)
- `exp` (Expiration time)
- `iss` (Issuer)
- `aud` (Audience)

---

## 3) Files included

- `secure_verify_jwt.py` — the demo script that creates & verifies JWTs.

(If you received additional files or images with this project, that security checklist image highlights common authentication weaknesses — see the **Recommended security improvements** section.)

---

## 4) Quick start — run locally

### Prerequisites
- Python 3.8+ recommended
- `pip` available

### Create a virtual environment

**Windows (cmd / PowerShell)**
```powershell
python -m venv .venv
# activate (PowerShell)
.venv\Scripts\Activate.ps1
# or cmd:
.venv\Scripts\activate.bat
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install dependency
The demo uses PyJWT. Install it:
```bash
pip install PyJWT
```

> Tip: pin a version in `requirements.txt` if you will track dependencies:
> ```
> PyJWT>=2.6.0
> ```

### Run the script
```bash
python secure_verify_jwt.py
```

You should see output similar to:
```
Token: <eyJ0eXAi...>
Verified payload: {'role': 'user', 'iat': 1700000000, 'exp': 1700000300, 'iss': 'demo', 'aud': 'demo-clients'}
```

---

## 5) Deep dive: `secure_verify_jwt.py` explained

Below is a simple annotated explanation of the functions in the script.

```python
# Secure: verify JWT signature and claims
import jwt, datetime

SECRET = "super-secret-key"  # demo only; rotate + store securely

def make_token():
    now = datetime.datetime.utcnow()
    return jwt.encode(
        {
            "role": "user",
            "iat": now,
            "exp": now + datetime.timedelta(minutes=5),
            "iss":"demo",
            "aud":"demo-clients"
        },
        SECRET, algorithm="HS256"
    )

def verify_token(token: str):
    return jwt.decode(token, SECRET, algorithms=["HS256"], issuer="demo", audience="demo-clients")

if __name__ == "__main__":
    tok = make_token()
    print("Token:", tok)
    print("Verified payload:", verify_token(tok))
```

- `SECRET` is the symmetric signing key (HS256). **Never** hardcode secrets in production.
- `make_token()` creates a token with claims and a 5-minute expiration.
- `verify_token()` decodes and verifies the token:
  - checks signature using `SECRET`
  - checks `iss` and `aud` claims
  - checks `exp` (expiration) automatically
- `jwt.encode` returns a compact JWT (a string); `jwt.decode` returns the verified payload as a Python dict.

---

## 6) Environment variables & securing secrets

**Do NOT commit secrets**. Use environment variables or secret managers.

Recommended change: read secret from environment:

```python
import os
SECRET = os.environ.get("JWT_SECRET", "super-secret-key-for-dev-only")
```

**Set environment variable**

**macOS / Linux**
```bash
export JWT_SECRET="a_really_long_random_secret_here"
```

**Windows (PowerShell)**
```powershell
$env:JWT_SECRET = "a_really_long_random_secret_here"
```

**Windows (persist)**
```powershell
setx JWT_SECRET "a_really_long_random_secret_here"
```
(reopen shell for `setx` to take effect)

**Use a secrets manager in production**
- AWS KMS + Secrets Manager / Parameter Store
- HashiCorp Vault
- GCP Secret Manager
- Azure Key Vault

**Consider asymmetric signing (RSA/EC)**
- Use `RS256` (private key to sign, public key to verify).
- Allows rotating keys and sharing public key with other services without exposing the private key.

Example: generate keys (openssl)
```bash
openssl genpkey -algorithm RSA -out private.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -in private.pem -pubout -out public.pem
```

Example usage with PyJWT:
```python
# sign
jwt.encode(payload, open("private.pem").read(), algorithm="RS256")

# verify
jwt.decode(token, open("public.pem").read(), algorithms=["RS256"], audience="demo-clients", issuer="demo")
```

---

## 7) Common runtime errors & troubleshooting

- `jwt.ExpiredSignatureError` — token expired (check system clock and `exp` value).
- `jwt.InvalidAudienceError` — `aud` claim mismatched.
- `jwt.InvalidIssuerError` — `iss` claim mismatched.
- `jwt.DecodeError` — signature invalid or token malformed.

If token verification fails:
1. Confirm the signing secret/key used to encode and decode match (and algorithm).
2. Check system time — wrong system clock can make `iat`/`exp` invalid.
3. Print token and payload (careful not to leak in logs) for debugging.

---

## 8) Recommended security improvements & checklist

The demo intentionally shows basic behavior. For production, consider implementing the following:

**From the authentication checklist (common pitfalls to avoid):**
- Don’t allow weak or common passwords.
- Invalidate a user’s session after they log out (support token revocation/blacklist).
- Protect against brute-force: account lockouts, CAPTCHA, and rate limiting.
- Implement Multi-Factor Authentication (MFA).

**Token & session best practices**
- Use short-lived access tokens (e.g., 5–15 minutes) + refresh tokens.
- Keep refresh tokens highly protected and store them server-side or in secure httpOnly cookies.
- Implement a token revocation/blacklist (e.g., store revoked token jti values in Redis).
- Rotate signing keys periodically and support key IDs (`kid`) in token header.
- Log auth events (issued, refreshed, revoked) for auditability.
- Use HTTPS everywhere, set `Secure` and `HttpOnly` flags on cookies.

**Hardening cryptography**
- Prefer RS256/ES256 for distributed systems (private key signs, public verifies).
- When using HS256, keep the secret long and random (>= 32 bytes).

---

## 9) Unit testing example with pytest

Create `tests/test_jwt.py`:

```python
import jwt
import datetime
import pytest
from secure_verify_jwt import make_token, verify_token
import secure_verify_jwt as module

def test_make_and_verify_token():
    tok = make_token()
    payload = verify_token(tok)
    assert payload["role"] == "user"
    assert payload["iss"] == "demo"
    assert payload["aud"] == "demo-clients"

def test_expired_token_raises():
    now = datetime.datetime.utcnow()
    expired = jwt.encode(
        {"role": "user", "iat": now - datetime.timedelta(hours=1),
         "exp": now - datetime.timedelta(minutes=1), "iss":"demo", "aud":"demo-clients"},
        module.SECRET, algorithm="HS256"
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        module.verify_token(expired)
```

Run tests:
```bash
pytest -q
```

---

## 10) Simple Jenkins pipeline example

A small Jenkinsfile (declarative) to set up Python, install deps, then run tests:

```groovy
pipeline {
  agent any

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Setup Python') {
      steps {
        sh 'python3 -m venv .venv'
        sh '. .venv/bin/activate && pip install --upgrade pip'
        sh '. .venv/bin/activate && pip install -r requirements.txt'
      }
    }

    stage('Run tests') {
      steps {
        sh '. .venv/bin/activate && pytest -q'
      }
    }
  }
}
```

> On Windows Jenkins agents replace `sh` with `bat` and use Windows activation commands.

---

## 11) Next steps / further reading

- Read RFC 7519 (JWT spec)
- PyJWT docs: https://pyjwt.readthedocs.io/
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP: Token-based authentication best practices

---

## Notes

- This file is intended for beginners — keep experimenting and consider using managed identity/auth tools (Auth0, AWS Cognito, Okta) for production use.
- Replace hard-coded secrets before any real deployment.
- Consider storing tokens in secure cookies and using TLS (HTTPS) at all times.

---

