"""
run_cases.py - run a skill on test cases and check the output against its contract.

    python tools/run_cases.py <skill-folder> <cases.jsonl> [--out outputs/]

How it works (a tiny imitation of an agent that has already triggered the skill):
  system prompt = SKILL.md body  (+ every file in references/ and assets/,
                                    labelled, i.e. Level 3 loaded on demand)
  user message  = the case's input (inline text, or a file path via "input_file")

Optional "action": run the skill's Action first and give the model its result, as if the
agent had called the tool. Paths in "cmd" are relative to the skill folder, "input_file"
to the cases file:
  "action": {"cmd": ["python", "scripts/x.py"], "input_file": "inputs/case1.json"}

Each line of cases.jsonl:
  {"id": "inv-01", "input_file": "samples/invoice_01.txt",
   "expect_status": "OK", "must_contain": ["Vendor", "GSTIN", "Total"]}

A case PASSES when:
  * the output has a line 'Status: <VALUE>' and VALUE == expect_status
  * every string in must_contain appears in the output (case-insensitive)
Outputs are saved to --out so you can read them.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skilllib import read_skill  # noqa: E402
from llm_adapter import chat  # noqa: E402


def build_system(skill_dir):
    _, body, _ = read_skill(skill_dir)
    parts = [body.strip()]
    for sub in ("references", "assets"):
        d = Path(skill_dir) / sub
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix in {".md", ".txt", ".json", ".csv"} and f.name != "README.md":
                    parts.append(f"\n--- {sub}/{f.name} ---\n" + f.read_text(encoding="utf-8"))
    return "\n".join(parts)


def run_action(skill_dir, base, action):
    """Simulate the agent having called the skill's Action: run it, hand the result to the model."""
    import subprocess
    cmd = [sys.executable if x == "python" else x for x in action["cmd"]]
    stdin = (base / action["input_file"]).read_text(encoding="utf-8") if "input_file" in action else ""
    p = subprocess.run(cmd, cwd=skill_dir, input=stdin, capture_output=True, text=True, timeout=60)
    shown = " ".join(action["cmd"])
    return f"[Tool result from `{shown}` (exit {p.returncode})]\n{p.stdout.strip() or p.stderr.strip()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir")
    ap.add_argument("cases")
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()

    system = build_system(a.skill_dir)
    base = Path(a.cases).parent
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = [json.loads(l) for l in Path(a.cases).read_text(encoding="utf-8").splitlines() if l.strip()]

    passed = 0
    for c in cases:
        if "input_file" in c:
            p = Path(c["input_file"])
            if not p.exists():
                p = base / c["input_file"]
            user = p.read_text(encoding="utf-8")
        else:
            user = c["input"]
        if "action" in c:
            user += "\n\n" + run_action(a.skill_dir, base, c["action"])
        reply = chat(system, user)
        (out / f"{c['id']}.md").write_text(reply, encoding="utf-8")

        problems = []
        # tolerant of markdown: "Status: X", "**Status:** X", "Status: `X`", "| Status | X |", any case
        m = re.search(r"(?im)^[\s*|`_>-]*status[\s*`_]*[:|][\s*`_|]*([A-Za-z_]+)", reply)
        got = m.group(1).upper() if m else None
        if got is None:
            problems.append("no 'Status: VALUE' line")
        elif got != c["expect_status"]:
            problems.append(f"status {got}, expected {c['expect_status']}")
        for s in c.get("must_contain", []):
            if s.lower() not in reply.lower():
                problems.append(f"missing '{s}'")
        ok = not problems
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {c['id']:<14} " + ("; ".join(problems) if problems else f"Status: {got}"))

    print(f"\n{passed}/{len(cases)} cases match the output contract. Outputs saved in {out}/")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
