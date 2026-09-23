# Secure: verify JWT signature and claims
import jwt, datetime # type: ignore

SECRET = "super-secret-key"  # demo only; rotate + store securely

def make_token():
    now = datetime.datetime.now(datetime.timezone.utc)
    return jwt.encode(
        {"role": "user", "iat": now, "exp": now + datetime.timedelta(minutes=5), "iss":"demo", "aud":"demo-clients"},
        SECRET, algorithm="HS256"
    )

def verify_token(token: str):
    return jwt.decode(token, SECRET, algorithms=["HS256"], issuer="demo", audience="demo-clients")

if __name__ == "__main__":
    tok = make_token()
    print("Token:", tok)
    print("Verified payload:", verify_token(tok))
