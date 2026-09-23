# Insecure: decode a JWT without verifying signature/claims
import base64, json

def decode_jwt_unsafe(token: str) -> dict:
    try:
        header, payload, signature = token.split(".")
        def b64d(s): 
            pad = "=" * (-len(s) % 4)
            return json.loads(base64.urlsafe_b64decode(s + pad).decode())
        return {"header": b64d(header), "payload": b64d(payload)}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    fake = "eyJhbGciOiJub25lIn0" + "." + "eyJyb2xlIjoiYWRtaW4ifQ" + ".ignored"
    print("fake token:", fake)
    print("Decoded (no verification!) =>", decode_jwt_unsafe(fake))
