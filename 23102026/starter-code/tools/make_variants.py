"""
tools/make_variants.py - TRAINER ONLY. Build the student starter from this solution tree.

    python tools/make_variants.py <solution_dir> <student_out_dir>

* Python files: drop "# >>> SOLUTION ... # <<< SOLUTION" blocks, un-comment
  "# >>> STARTER ... # <<< STARTER" blocks, remove the marker lines.
* Skips trainer-only files (TRAINER_NOTES.md, tools/, .env, caches, node_modules).
"""
import re
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {"tools", "__pycache__", ".pytest_cache", "node_modules", ".venv", ".git"}
SKIP_FILES = {"TRAINER_NOTES.md", ".env"}


def to_starter(text: str) -> str:
    out, mode = [], None
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if s == "# >>> SOLUTION":
            mode = "sol"
            continue
        if s == "# <<< SOLUTION":
            mode = None
            continue
        if s == "# >>> STARTER":
            mode = "start"
            continue
        if s == "# <<< STARTER":
            mode = None
            continue
        if mode == "sol":
            continue
        if mode == "start":
            line = re.sub(r"^(\s*)# ?", r"\1", line, count=1)
        out.append(line)
    return "".join(out)


def main(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if any(part in SKIP_DIRS for part in rel.parts) or path.name in SKIP_FILES:
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".py":
            target.write_text(to_starter(path.read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(path, target)
    print(f"student tree written to {dst}")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
