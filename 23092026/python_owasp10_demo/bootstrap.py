# Create a venv and install dependencies (prefers local ./vendor wheels if present)
# Usage: python bootstrap.py
import os, sys, subprocess, venv
ROOT = os.path.dirname(__file__)
VENV = os.path.join(ROOT, ".venv")
REQ = os.path.join(ROOT, "requirements.txt")
VENDOR = os.path.join(ROOT, "vendor")
if not os.path.isdir(VENV):
    print("Creating venv at", VENV)
    venv.EnvBuilder(with_pip=True).create(VENV)
PIP = os.path.join(VENV, "Scripts", "pip.exe") if os.name == "nt" else os.path.join(VENV, "bin", "pip")
args = [PIP, "install", "-r", REQ]
if os.path.isdir(VENDOR) and os.listdir(VENDOR):
    args = [PIP, "install", "--no-index", "--find-links", VENDOR, "-r", REQ]
print("Running:", " ".join(args))
subprocess.check_call(args)
print("Done. Activate the venv and run demos.")
