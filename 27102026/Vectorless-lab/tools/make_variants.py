"""
tools/make_variants.py - TRAINER ONLY. Build the student starter from this solution tree.

    python tools/make_variants.py <solution_dir> <student_out_dir> [--labs lab2,lab3]

* Python files: drop "# >>> SOLUTION ... # <<< SOLUTION" blocks, un-comment
  "# >>> STARTER ... # <<< STARTER" blocks, remove the marker lines.
* A marker may carry a lab tag: "# >>> SOLUTION lab3". Untagged markers are lab2.
  --labs picks which labs become TODOs (default: all). Blocks of other labs keep
  their SOLUTION and lose their STARTER, so e.g. "--labs lab3" gives a Lab 3
  starter with Lab 1 and Lab 2 already solved.
* Skips trainer-only files (TRAINER_NOTES.md, tools/, .env, caches, node_modules).
"""
import re
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {"tools", "__pycache__", ".pytest_cache", "node_modules", ".venv", ".git", ".cache"}
SKIP_FILES = {"TRAINER_NOTES.md", ".env"}


_MARK = re.compile(r"^# (>>>|<<<) (SOLUTION|STARTER)(?:\s+(\w+))?$")


def to_starter(text: str, labs: set[str] | None = None) -> str:
    out, mode = [], None
    for line in text.splitlines(keepends=True):
        m = _MARK.match(line.strip())
        if m:
            opening, kind, tag = m.group(1) == ">>>", m.group(2), m.group(3) or "lab2"
            if not opening:
                mode = None
            else:
                selected = labs is None or tag in labs
                if kind == "SOLUTION":
                    mode = "sol" if selected else "keep"
                else:
                    mode = "start" if selected else "drop"
            continue
        if mode in ("sol", "drop"):
            continue
        if mode == "start":
            line = re.sub(r"^(\s*)# ?", r"\1", line, count=1)
        out.append(line)
    return "".join(out)


def main(src: Path, dst: Path, labs: set[str] | None = None) -> None:
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
            target.write_text(to_starter(path.read_text(encoding="utf-8"), labs), encoding="utf-8")
        else:
            shutil.copy2(path, target)
    print(f"student tree written to {dst} (TODOs for: {', '.join(sorted(labs)) if labs else 'all labs'})")


if __name__ == "__main__":
    args = sys.argv[1:]
    chosen = None
    if "--labs" in args:
        i = args.index("--labs")
        chosen = {t.strip() for t in args[i + 1].split(",") if t.strip()}
        del args[i : i + 2]
    main(Path(args[0]).resolve(), Path(args[1]).resolve(), chosen)
