"""
gate.py - Tier 1 security gate: does the code do anything the manifest does not declare?

    python tools/gate.py path/to/skill-folder

It reads the permission manifest from SKILL.md frontmatter:

    allowed-tools: Read Bash(python:*)
    metadata:
      fil.permissions:
        data_scopes: [ap.invoices:read]
        network_egress: none            # or a list of hosts
        writes: [./output/]             # or none
        credentials: none               # or a list of env var names
        side_effects: none              # or a list, e.g. [send_email]

…then scans every .py file under scripts/ (static analysis with Python's ast):
  network      import/use of requests, httpx, urllib, aiohttp, socket, http.client
  write        open(..., 'w'|'a'|'x'|'+'), Path.write_text / write_bytes, shutil copy/move
  credentials  os.environ / os.getenv / os.environ.get
  side effect  subprocess, os.system, smtplib
Every finding must be covered by a declaration, or the gate FAILS.
Static gates catch a lot, not everything: a human review is still required.
Exit code 0 = PASS, 1 = FAIL.
"""
import ast
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skilllib import read_skill  # noqa: E402

NET_MODS = {"requests", "httpx", "urllib", "urllib3", "aiohttp", "socket", "http"}
FX_MODS = {"subprocess", "smtplib"}


def as_list(v):
    if v is None or (isinstance(v, str) and v.strip().lower() in {"none", ""}):
        return []
    return v if isinstance(v, list) else [v]


class Scanner(ast.NodeVisitor):
    def __init__(self, fname, tree):
        self.f, self.found = fname, []
        # module-level string constants, so open(LOG_PATH, "a") can be resolved
        self.consts = {}
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        self.consts[t.id] = n.value.value

    def add(self, kind, node, detail, path=None):
        self.found.append((kind, f"{self.f}:{node.lineno}", detail, path))

    def resolve(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return self.consts.get(node.id)
        return None

    def visit_Import(self, node):
        for a in node.names:
            root = a.name.split(".")[0]
            if root in NET_MODS:
                self.add("network", node, f"import {a.name}")
            if root in FX_MODS:
                self.add("side_effect", node, f"import {a.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        root = (node.module or "").split(".")[0]
        if root in NET_MODS:
            self.add("network", node, f"from {node.module} import …")
        if root in FX_MODS:
            self.add("side_effect", node, f"from {node.module} import …")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == "os" and node.attr in {"environ", "getenv"}:
            self.add("credentials", node, f"os.{node.attr}")
        if isinstance(node.value, ast.Name) and node.value.id == "os" and node.attr == "system":
            self.add("side_effect", node, "os.system")
        self.generic_visit(node)

    def visit_Call(self, node):
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id == "open":
            mode = None
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if isinstance(mode, str) and any(ch in mode for ch in "wax+"):
                target = ast.unparse(node.args[0]) if node.args else "?"
                path = self.resolve(node.args[0]) if node.args else None
                self.add("write", node, f"open({target}, '{mode}')", path)
        if isinstance(fn, ast.Attribute) and fn.attr in {"write_text", "write_bytes", "mkdir", "unlink", "rmdir"}:
            self.add("write", node, f"{ast.unparse(fn)}()")
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == "shutil":
            self.add("write", node, f"shutil.{fn.attr}()")
        self.generic_visit(node)


def main(folder):
    folder = Path(folder)
    front, _, _ = read_skill(folder)
    perms = ((front.get("metadata") or {}).get("fil.permissions") or {})
    declared = {
        "network": as_list(perms.get("network_egress")),
        "write": as_list(perms.get("writes")),
        "credentials": as_list(perms.get("credentials")),
        "side_effect": as_list(perms.get("side_effects")),
    }
    problems = []
    if not front.get("allowed-tools"):
        problems.append("manifest: 'allowed-tools' is missing from the frontmatter")
    if not perms:
        problems.append("manifest: 'metadata: fil.permissions' block is missing")
    for key in ("data_scopes", "network_egress", "writes", "credentials", "side_effects"):
        if perms and key not in perms:
            problems.append(f"manifest: '{key}' not declared (write 'none' if it does not apply)")

    findings = []
    for py in sorted((folder / "scripts").rglob("*.py")) if (folder / "scripts").is_dir() else []:
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError as e:
            problems.append(f"{py.name}: cannot parse ({e})")
            continue
        s = Scanner(str(py.relative_to(folder)), tree)
        s.visit(tree)
        findings += s.found

    print(f"Security gate for: {folder.name}")
    print(f"Declared  network={declared['network'] or 'none'}  writes={declared['write'] or 'none'}  "
          f"credentials={declared['credentials'] or 'none'}  side_effects={declared['side_effect'] or 'none'}\n")
    used = {k: False for k in declared}
    allowed_dirs = [os.path.normpath(str(p)) for p in declared["write"]]
    for kind, where, detail, path in findings:
        covered = bool(declared[kind])
        note = ""
        if kind == "write" and covered:
            if path is None:
                note = "  (path not static: reviewer must check it stays inside " + str(declared["write"]) + ")"
            elif not any(os.path.normpath(path) == d or os.path.normpath(path).startswith(d + os.sep)
                         for d in allowed_dirs):
                covered = False
                note = f"  (writes to '{path}', outside declared {declared['write']})"
        used[kind] = used[kind] or covered
        print(f"[{'ok  ' if covered else 'FAIL'}] {kind:<12} {where:<28} {detail}{note}")
        if not covered:
            problems.append(f"{kind} at {where} ({detail}) is not covered by the manifest{note}")
    if not findings:
        print("(no network, write, credential or side-effect code found in scripts/)")
    for kind, vals in declared.items():
        if vals and not used[kind]:
            print(f"[warn] {kind} is declared ({vals}) but no code uses it: remove it (least privilege)")

    print()
    for p in problems:
        print(" -", p)
    print("RESULT:", "PASS" if not problems else f"FAIL ({len(problems)} problem(s))")
    return 0 if not problems else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
