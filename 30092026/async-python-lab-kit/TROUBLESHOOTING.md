# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `'python' is not recognized` (Windows) | Python not on PATH | use `py -3.13 ...` or reinstall with "Add to PATH" |
| `Activate.ps1 cannot be loaded ... running scripts is disabled` | PowerShell execution policy | use `cmd` + `.venv\Scripts\activate.bat`, or call `.venv\Scripts\python.exe` directly |
| `fastapi: command not found` | venv not active / Scripts not on PATH | activate the venv, or `python -m uvicorn main:app --reload` |
| `ModuleNotFoundError: No module named 'app'` (Lab 8) | running from wrong folder | `cd lab08_capstone/starter` (the folder with `pytest.ini`) |
| `[Errno 98/10048] address already in use` | an old server still running | stop it with `Ctrl+C`, or use `--port 8002` |
| `httpx2.ConnectError: ... Connection refused` | the server for Lab 6/7 is not running | start it in a second terminal |
| `SyntaxError` on `except*` or `AttributeError: TaskGroup` | Python older than 3.11 | upgrade Python |
| `RuntimeWarning: coroutine ... was never awaited` | missing `await` | add `await` (or `create_task`) |
| `RuntimeError: asyncio.run() cannot be called from a running event loop` | running inside Jupyter | in notebooks just `await main()` |
| Program is async but not faster | awaiting one-by-one, or a blocking call inside | use `gather`/`TaskGroup`; remove `time.sleep`/`requests` |
| pip SSL / proxy errors | corporate proxy | `pip install --proxy http://host:port ...` or the internal mirror |
| `curl` behaves oddly in PowerShell | `curl` is an alias of `Invoke-WebRequest` | use `curl.exe`, Swagger UI (`/docs`) or the lab's `client.py` |
