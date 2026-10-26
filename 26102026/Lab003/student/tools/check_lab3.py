"""
check_lab3.py - tells you which Lab 3 step is not done yet, and exactly how to fix it.

    python tools/check_lab3.py

Run it after every step. It stops at the FIRST problem it finds.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals" / "triggers.jsonl"
SKILLS = ROOT / "skills"
TARGET = "invoice-summary-formatter"
SKILL_MD = SKILLS / TARGET / "SKILL.md"


def ok(msg):
    print(f"[OK]   {msg}")


def stop(step, problem, fix, file):
    print(f"\n[FIX]  Step {step}: {problem}")
    print(f"       -> {fix}")
    print(f"       File: {Path(file).relative_to(ROOT).as_posix()}")
    sys.exit(1)


names = {d.name for d in SKILLS.iterdir() if (d / "SKILL.md").exists()} | {"NONE"}

# ------------------------------------------------------------------ Step 1
if not EVALS.exists():
    stop(1, "evals/triggers.jsonl does not exist yet.",
         "Copy evals/triggers_template.jsonl to evals/triggers.jsonl, then add your lines.", EVALS.parent)

rows = []
for n, line in enumerate(EVALS.read_text(encoding="utf-8").splitlines(), start=1):
    if not line.strip():
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError as e:
        stop(1, f"line {n} is not valid JSON ({e.msg}).",
             'Each line must look exactly like: {"prompt": "…", "expected": "…"}  '
             "(double quotes, a comma between the two parts, no comma at the end of the line).", EVALS)
    if set(row) != {"prompt", "expected"}:
        stop(1, f"line {n} must have exactly two keys, prompt and expected (found: {', '.join(row)}).",
             'Write it as {"prompt": "…", "expected": "…"}', EVALS)
    if row["expected"] not in names:
        stop(1, f"line {n}: expected = {row['expected']!r} is not a skill name.",
             "Use one of: " + ", ".join(sorted(names)), EVALS)
    rows.append(row)

pos = sum(1 for r in rows if r["expected"] == TARGET)
neg = len(rows) - pos
if len(rows) != 10 or pos != 5:
    stop(1, f"you have {len(rows)} prompts: {pos} should load {TARGET}, {neg} should not.",
         f"You need exactly 10: 5 with \"expected\": \"{TARGET}\" and 5 near-misses "
         "(a decoy skill name or NONE).", EVALS)
ok(f"Step 1  triggers.jsonl has 10 prompts (5 should load, 5 near-misses)")

# ------------------------------------------------------------------ Step 4
text = SKILL_MD.read_text(encoding="utf-8")
m = re.search(r"^description:\s*(.*)$", text, re.M)
desc = m.group(1).strip() if m else ""
if not desc:
    stop(4, "SKILL.md has no description line.",
         "Line 3 of SKILL.md must start with  description:", SKILL_MD)
if "finance stuff" in desc:
    print("[--]   Step 4  description is still the weak starter one. "
          "That is expected for the Step 2 baseline run.")
    sys.exit(0)
if not re.search(r"use when", desc, re.I):
    stop("4a", "the description does not say 'Use when …'.",
         "Replace the description with the Step 4a text.", SKILL_MD)
ok("Step 4a description says 'Use when …'")
if not re.search(r"do not use", desc, re.I):
    stop("4b", "the description does not say 'Do not use …' yet.",
         "Add the Step 4b sentence to the end of the description line.", SKILL_MD)
ok("Step 4b description says 'Do not use …'")
if "\n" in desc or len(desc) > 1024:
    stop(4, "the description must be ONE line, at most 1024 characters.",
         "Keep everything after 'description:' on the same line.", SKILL_MD)

print("\nAll edits done. Now run the trigger eval (Step 5).")
