"""Day 1 sanity check: python scripts/check_setup.py"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fundlens import llm_client  # noqa: E402
from fundlens.config import settings  # noqa: E402

ok = True
print(f"LLM mode         : {settings.llm_mode}")
print(f"Kit folder       : {settings.kit_dir}")
manifest = settings.kit_dir / "MANIFEST.sha256"
if not manifest.exists():
    print("[FAIL] MANIFEST.sha256 not found - is FUNDLENS_KIT_DIR pointing at the kit root?")
    sys.exit(1)
bad = 0
for line in manifest.read_text().splitlines():
    digest, rel = line.split("  ", 1)
    p = settings.kit_dir / rel
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
        bad += 1
        print(f"[FAIL] changed or missing: {rel}")
print(f"Starter corpus   : {'intact' if bad == 0 else f'{bad} file(s) changed - restore them from the zip'}")
ok &= bad == 0
try:
    out = llm_client.chat([{"role": "user", "content": "Reply with the single word: pong"}])
    vec = llm_client.embed(["hello"])[0]
    print(f"Chat call        : OK -> {out[:40]!r}")
    print(f"Embedding call   : OK -> dim {len(vec)}")
except Exception as exc:  # noqa: BLE001
    ok = False
    print(f"[FAIL] LLM call: {exc}. Check .env, or set FUNDLENS_LLM_MODE=mock to work offline.")
print("ALL GOOD" if ok else "FIX THE ITEMS ABOVE")
sys.exit(0 if ok else 1)
