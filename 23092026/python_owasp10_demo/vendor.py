# Download wheels for offline install into ./vendor
# Usage: python vendor.py
import subprocess, sys, os
REQ = os.path.join(os.path.dirname(__file__), "requirements.txt")
VENDOR = os.path.join(os.path.dirname(__file__), "vendor")
os.makedirs(VENDOR, exist_ok=True)
cmd = [sys.executable, "-m", "pip", "download", "-d", VENDOR, "-r", REQ, "--only-binary=:all:"]
print("Running:", " ".join(cmd))
subprocess.check_call(cmd)
print("Done. Wheels stored in ./vendor")
