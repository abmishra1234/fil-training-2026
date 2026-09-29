"""Step 0 - verify your machine is ready for the Async Python labs.

Run:  python 00_setup/verify_setup.py
Every line should say OK. Fix any FAIL before class starts.
"""
import asyncio
import importlib
import sys

OK, FAIL = "OK  ", "FAIL"
problems = 0

major, minor = sys.version_info[:2]
if (major, minor) >= (3, 11):
    print(f"[{OK}] Python {major}.{minor} (need 3.11+, TaskGroup and asyncio.timeout are used)")
else:
    problems += 1
    print(f"[{FAIL}] Python {major}.{minor} is too old - install Python 3.13 (3.11 minimum)")

for pkg in ("fastapi", "uvicorn", "httpx2", "pydantic", "pytest", "pytest_asyncio"):
    try:
        mod = importlib.import_module(pkg)
        print(f"[{OK}] {pkg:<15} {getattr(mod, '__version__', '')}")
    except ImportError:
        problems += 1
        print(f"[{FAIL}] {pkg:<15} missing -> pip install -r requirements.txt")


async def smoke_test() -> str:
    await asyncio.sleep(0.1)
    return "event loop works"

print(f"[{OK}] asyncio: {asyncio.run(smoke_test())}")
print("\nAll good - you are ready!" if problems == 0 else f"\n{problems} problem(s) found - fix them first.")
