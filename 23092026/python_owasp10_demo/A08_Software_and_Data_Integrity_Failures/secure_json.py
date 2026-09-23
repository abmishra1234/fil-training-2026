# Secure: parse untrusted data as JSON (treated as data, not code)
import json

malicious_payload = '{"command": "import os; os.system(\\"echo hacked\\")"}'
data = json.loads(malicious_payload)
print(f"Data parsed safely: {data}")
