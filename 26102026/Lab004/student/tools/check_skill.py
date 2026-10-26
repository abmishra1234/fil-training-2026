"""
check_skill.py - lint a skill folder against the Tier 1 Instruction + Trigger rules.

    python tools/check_skill.py path/to/skill-folder

Checks
  Trigger      : name + description present; 'Use when' and 'Do not use' clauses;
                 description <= 1024 characters; name matches folder name
  Instruction  : the five sections (Role, Procedure, Decision rules,
                 Output contract, Examples); body < 500 lines; < 5,000 tokens
  Hygiene      : no secrets, no placeholder '…' / TODO left behind
Exit code 0 = PASS, 1 = FAIL.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skilllib import read_skill, estimate_tokens  # noqa: E402

SECTIONS = ["role", "procedure", "decision rules", "output contract", "examples"]
SECRET = re.compile(r"(api[_-]?key|password|secret|token)\s*[:=]\s*\S{6,}|sk-[A-Za-z0-9]{10,}", re.I)


def main(folder):
    folder = Path(folder)
    front, body, full = read_skill(folder)
    results = []

    def check(ok, label, hint=""):
        results.append((ok, label, hint))

    name = str(front.get("name", ""))
    desc = str(front.get("description", ""))
    check(bool(name), "Trigger: frontmatter has 'name'")
    check(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name or "x-") is not None and len(name) <= 64,
          "Trigger: name is lowercase-with-hyphens, <= 64 chars")
    check(name == folder.name, "Trigger: name matches folder name",
          f"folder is '{folder.name}', name is '{name}'")
    check(bool(desc), "Trigger: frontmatter has 'description'")
    check(len(desc) <= 1024, "Trigger: description <= 1024 characters", f"now {len(desc)}")
    check(re.search(r"use when", desc, re.I) is not None, "Trigger: says 'Use when…'",
          "Describe the positive cases in the user's own words")
    check(re.search(r"do not use", desc, re.I) is not None, "Trigger: says 'Do not use for…'",
          "Name the near-misses the skill must ignore")

    heads = [h.strip().lower() for h in re.findall(r"^#{1,3}\s+(.+)$", body, re.M)]
    for s in SECTIONS:
        check(any(h.startswith(s) for h in heads), f"Instruction: has '## {s.title()}' section")

    lines = body.count("\n") + 1
    toks = estimate_tokens(body)
    check(lines < 500, "Instruction: body < 500 lines", f"now {lines}")
    check(toks < 5000, "Instruction: body < 5,000 tokens", f"now ~{toks}")

    check(SECRET.search(full) is None, "Hygiene: no secrets in SKILL.md",
          "Credentials come from connectors, never from instructions")
    check("…" not in full and "TODO" not in full, "Hygiene: no '…' or TODO placeholders left")

    width = max(len(r[1]) for r in results)
    for ok, label, hint in results:
        mark = "PASS" if ok else "FAIL"
        extra = f"   -> {hint}" if (hint and not ok) else ""
        print(f"[{mark}] {label.ljust(width)}{extra}")
    failed = sum(1 for r in results if not r[0])
    print(f"\n{len(results) - failed}/{len(results)} checks passed  "
          f"(body: {lines} lines, ~{toks} tokens)")
    print("RESULT:", "PASS" if failed == 0 else "FAIL")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
