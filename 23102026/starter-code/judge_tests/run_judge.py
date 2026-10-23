"""
judge_tests/run_judge.py - run the 30 judge tests and write the Judge Test report.

    python judge_tests/run_judge.py --student "Your Name"

Writes judge_tests/reports/judge_report.md (submit this) and judge_report.json.
A judge test (JT01..JT30) scores 1 point only if ALL its cases pass.
"""
from __future__ import annotations

import argparse
import ast
import json
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
JT = re.compile(r"test_(JT\d{2})_\w+")


def catalogue() -> dict[str, dict]:
    """JT id -> {title, group, file} read from the test files' docstrings."""
    cat: dict[str, dict] = {}
    for f in sorted(HERE.glob("test_*.py")):
        mod = ast.parse(f.read_text(encoding="utf-8"))
        group = (ast.get_docstring(mod) or f.stem).strip().splitlines()[0]
        group = group.split(":")[0].strip()
        for node in mod.body:
            if isinstance(node, ast.FunctionDef) and (m := JT.match(node.name)):
                doc = (ast.get_docstring(node) or node.name).strip()
                cat[m.group(1)] = {"title": " ".join(doc.split()), "group": group, "file": f.name, "function": node.name}
    return cat


def run_pytest(xml_path: Path) -> int:
    cmd = [sys.executable, "-m", "pytest", str(HERE), "-q", "-p", "no:cacheprovider", "--rootdir", str(ROOT),
           "-o", "testpaths=judge_tests", f"--junitxml={xml_path}"]
    return subprocess.call(cmd, cwd=ROOT)


def parse(xml_path: Path) -> dict[str, list[dict]]:
    cases: dict[str, list[dict]] = {}
    if not xml_path.exists():
        return cases
    for tc in ET.parse(xml_path).getroot().iter("testcase"):
        m = JT.search(tc.get("name", ""))
        if not m:
            continue
        bad = tc.find("failure") if tc.find("failure") is not None else tc.find("error")
        skipped = tc.find("skipped") is not None
        msg = ""
        if bad is not None:
            msg = (bad.get("message") or bad.text or "").strip().splitlines()[0][:220] if (bad.get("message") or bad.text) else "failed"
        cases.setdefault(m.group(1), []).append({
            "case": tc.get("name"), "passed": bad is None and not skipped, "message": msg,
            "seconds": float(tc.get("time") or 0),
        })
    return cases


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", default="(name not given)")
    ap.add_argument("--out", default=str(HERE / "reports"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    xml_path = out / "junit.xml"
    run_pytest(xml_path)

    cat, cases = catalogue(), parse(xml_path)
    rows, groups = [], {}
    for jt in sorted(cat):
        cs = cases.get(jt, [])
        passed = bool(cs) and all(c["passed"] for c in cs)
        info = cat[jt]
        rows.append({"id": jt, **info, "passed": passed, "cases": len(cs), "cases_passed": sum(c["passed"] for c in cs),
                     "failures": [c for c in cs if not c["passed"]]})
        g = groups.setdefault(info["group"], [0, 0])
        g[0] += int(passed)
        g[1] += 1
    score = sum(r["passed"] for r in rows)
    total = len(rows)
    meta = {"student": args.student, "generated": datetime.now().isoformat(timespec="seconds"),
            "python": platform.python_version(), "platform": platform.platform(), "score": score, "total": total}
    (out / "judge_report.json").write_text(json.dumps({**meta, "groups": groups, "tests": rows}, indent=2), encoding="utf-8")

    md = [f"# Judge Test report - Mini AI Gateway", "",
          f"**Student:** {args.student}  ", f"**Score:** {score} / {total}  ",
          f"**Generated:** {meta['generated']} · Python {meta['python']}", "", "## By group", "",
          "| Group | Passed |", "|---|---|"]
    md += [f"| {g} | {p} / {t} |" for g, (p, t) in groups.items()]
    md += ["", "## Tests", "", "| # | Result | Cases | Requirement verified |", "|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['id']} | {'PASS' if r['passed'] else '**FAIL**'} | {r['cases_passed']}/{r['cases']} | {r['title']} |")
    fails = [r for r in rows if not r["passed"]]
    if fails:
        md += ["", "## Failures (first line of each)", ""]
        for r in fails:
            for c in r["failures"] or [{"case": r["function"], "message": "not collected (import error?)"}]:
                md.append(f"- **{r['id']}** `{c['case']}` - {c['message']}")
    (out / "judge_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nJudge score: {score}/{total}  ->  {out / 'judge_report.md'}")
    return 0 if score == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
