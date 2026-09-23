@echo off
python bootstrap.py
call .venv\Scripts\activate
echo Examples:
echo   uvicorn A01_Broken_Access_Control.a01_insecure_access:app --port 5001
