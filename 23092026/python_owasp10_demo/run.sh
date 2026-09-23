#!/usr/bin/env bash
set -euo pipefail
python3 bootstrap.py
source .venv/bin/activate
echo "Examples:"
echo "  uvicorn A01_Broken_Access_Control.a01_insecure_access:app --port 5001"
