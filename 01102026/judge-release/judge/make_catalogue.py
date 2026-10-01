"""Regenerates TEST_CATALOGUE.md from the test docstrings (python make_catalogue.py)."""
import importlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "tests"))
from conftest import CATEGORIES  # noqa: E402

rows = []
for f in sorted((Path(__file__).parent / "tests").glob("test_*.py")):
    mod = importlib.import_module(f.stem)
    for name in dir(mod):
        fn = getattr(mod, name)
        if not name.startswith("test_") or not callable(fn):
            continue
        marks = getattr(fn, "pytestmark", [])
        cat = next((m.args[0] for m in marks if m.name == "cat"), "?")
        n = math.prod(len(m.args[1]) for m in marks if m.name == "parametrize") or 1
        tid, _, title = (fn.__doc__ or name).strip().splitlines()[0].partition(" ")
        rows.append((f.name, fn.__code__.co_firstlineno, cat, tid, title, n))
rows.sort(key=lambda r: (r[0], r[1]))
out = ["# Judge test catalogue", "",
       f"{len(rows)} test functions, {sum(r[5] for r in rows)} executed test cases (parametrised).", "",
       "| Category | Cases | Meaning |", "|---|---:|---|"]
for c, meaning in CATEGORIES.items():
    out.append(f"| {c} | {sum(r[5] for r in rows if r[2] == c)} | {meaning} |")
cur = None
for file, _, cat, tid, title, n in rows:
    if file != cur:
        out += ["", f"## {file}", "", "| ID | Category | Requirement verified | Cases |", "|---|---|---|---:|"]
        cur = file
    out.append(f"| {tid} | {cat} | {title} | {n} |")
Path(__file__).with_name("TEST_CATALOGUE.md").write_text("\n".join(out) + "\n")
print(len(rows), sum(r[5] for r in rows))
