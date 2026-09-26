"""Build the Excel test-case catalogue straight from the test docstrings (single source of truth)."""
import ast
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).parent / "tests"
AREAS = {"HLT": "Health", "AUTH": "Auth & Profile", "RBAC": "Roles & Access", "USR": "Users", "CAB": "Cabs",
         "BKG": "Bookings", "TRP": "Trips", "DRV": "Driver", "PAG": "Pagination", "E2E": "End-to-end",
         "RPT": "Reports (stretch)"}


def count_cases(fn: ast.FunctionDef, module_consts: dict) -> int:
    n = 1
    for dec in fn.decorator_list:
        if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize":
            arg = dec.args[1]
            if isinstance(arg, (ast.List, ast.Tuple)):
                n *= len(arg.elts)
            elif isinstance(arg, ast.Name) and arg.id in module_consts:
                n *= module_consts[arg.id]
            elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):  # X.keys()
                n *= module_consts.get(arg.func.value.id, 1)
    return n


def collect():
    rows = []
    for path in sorted(ROOT.rglob("test_*.py")):
        tree = ast.parse(path.read_text())
        consts = {}
        mod_ns = {}
        for node in tree.body:  # evaluate simple module-level list/dict sizes
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                name = node.targets[0].id
                if isinstance(node.value, (ast.List, ast.Dict, ast.Tuple)):
                    consts[name] = len(node.value.keys if isinstance(node.value, ast.Dict) else node.value.elts)
        if path.name == "test_full_rbac.py":  # FORBIDDEN is a comprehension; compute it
            sys.path[:0] = [str(ROOT), str(ROOT.parent)]
            import importlib.util
            spec = importlib.util.spec_from_file_location("rb", path)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            consts["FORBIDDEN"] = len(m.FORBIDDEN)
        for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
            doc = ast.get_docstring(fn) or ""
            m = re.match(r"\[(?P<id>[^\]]+)\]\s*(?P<ep>[^|]+)\|\s*(?P<rule>.+)", doc.splitlines()[0])
            if not m:
                raise SystemExit(f"bad docstring: {path}::{fn.name}")
            body = doc.splitlines()[1:]
            expect = " ".join(l.strip()[len("Expect:"):].strip() for l in body if l.strip().startswith("Expect:"))
            scenario = " ".join(l.strip() for l in body if not l.strip().startswith("Expect:"))
            tid = m["id"].strip()
            suite = {"S": "Simple", "F": "Full", "X": "Stretch"}[tid[0]]
            area = AREAS[tid.split("-")[1]]
            rel = path.relative_to(ROOT.parent).as_posix()
            rows.append([tid, suite, area, m["ep"].strip(), m["rule"].strip(), scenario, expect,
                         count_cases(fn, consts), f"{rel}::{fn.name}"])
    return rows


def main(out):
    rows = collect()
    wb = Workbook()
    head_fill = PatternFill("solid", fgColor="1F4E79")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)
    font = "Arial"
    headers = ["TC ID", "Suite", "Area", "Endpoint", "Rule / Spec ref", "Scenario (steps)", "Expected result",
               "Cases", "pytest node id", "Status", "Notes"]
    widths = [13, 9, 16, 30, 24, 60, 44, 7, 52, 11, 24]

    # ---- summary
    ws = wb.active
    ws.title = "Summary"
    ws["A1"] = "CabRoster — Test Case Catalogue"
    ws["A1"].font = Font(name=font, bold=True, size=14, color="1F4E79")
    ws["A2"] = ("Generated from test docstrings. 'Cases' counts parametrized variants; pytest reports one result "
                "per case. Fill the Status column (Pass / Fail / Blocked) on the suite sheets — totals below update.")
    ws["A2"].font = Font(name=font, italic=True, size=9, color="595959")
    ws.merge_cells("A2:H2")
    hdr = ["Area", "Simple: tests", "Simple: cases", "Full: tests", "Full: cases", "Stretch: cases",
           "Passed (Full)", "Failed (Full)"]
    for i, h in enumerate(hdr, 1):
        c = ws.cell(row=4, column=i, value=h)
        c.font = Font(name=font, bold=True, color="FFFFFF")
        c.fill = head_fill
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = border
    r = 5
    for area in AREAS.values():
        ws.cell(row=r, column=1, value=area)
        ws.cell(row=r, column=2, value=f"=COUNTIF('Simple Suite'!C:C,A{r})")
        ws.cell(row=r, column=3, value=f"=SUMIFS('Simple Suite'!H:H,'Simple Suite'!C:C,A{r})")
        ws.cell(row=r, column=4, value=f"=COUNTIF('Full Suite'!C:C,A{r})")
        ws.cell(row=r, column=5, value=f"=SUMIFS('Full Suite'!H:H,'Full Suite'!C:C,A{r},'Full Suite'!B:B,\"Full\")")
        ws.cell(row=r, column=6, value=f"=SUMIFS('Full Suite'!H:H,'Full Suite'!C:C,A{r},'Full Suite'!B:B,\"Stretch\")")
        ws.cell(row=r, column=7, value=f"=COUNTIFS('Full Suite'!C:C,A{r},'Full Suite'!J:J,\"Pass\")")
        ws.cell(row=r, column=8, value=f"=COUNTIFS('Full Suite'!C:C,A{r},'Full Suite'!J:J,\"Fail\")")
        r += 1
    ws.cell(row=r, column=1, value="TOTAL").font = Font(name=font, bold=True)
    for col in range(2, 9):
        L = get_column_letter(col)
        ws.cell(row=r, column=col, value=f"=SUM({L}5:{L}{r - 1})").font = Font(name=font, bold=True)
    for row in ws.iter_rows(min_row=5, max_row=r, max_col=8):
        for c in row:
            c.border = border
            if c.font.name != font:
                c.font = Font(name=font, bold=c.font.bold)
    for i, w in enumerate([20, 13, 13, 12, 12, 14, 13, 13], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[4].height = 30
    notes = [
        "How to run:",
        "  Simple suite (students):   pytest tests/simple",
        "  Full suite (grading):      pytest tests/full -m \"not stretch\"",
        "  Stretch (reports):         pytest -m stretch",
        "Pass mark suggestion: 100% of Simple; Full score = passed cases / total Full cases.",
    ]
    for i, t in enumerate(notes):
        ws.cell(row=r + 2 + i, column=1, value=t).font = Font(name=font, size=9, bold=(i == 0))

    # ---- suite sheets
    for title, pick in (("Simple Suite", lambda x: x[1] == "Simple"),
                        ("Full Suite", lambda x: x[1] in ("Full", "Stretch"))):
        s = wb.create_sheet(title)
        for i, h in enumerate(headers, 1):
            c = s.cell(row=1, column=i, value=h)
            c.font = Font(name=font, bold=True, color="FFFFFF")
            c.fill = head_fill
            c.alignment = Alignment(vertical="center", wrap_text=True)
            c.border = border
            s.column_dimensions[get_column_letter(i)].width = widths[i - 1]
        dv = DataValidation(type="list", formula1='"Pass,Fail,Blocked,Not run"', allow_blank=True)
        s.add_data_validation(dv)
        data = [x for x in rows if pick(x)]
        for ri, row in enumerate(data, 2):
            for ci, v in enumerate(row + ["", ""], 1):
                c = s.cell(row=ri, column=ci, value=v)
                c.font = Font(name=font, size=9)
                c.alignment = Alignment(vertical="top", wrap_text=True)
                c.border = border
                if ri % 2 == 0:
                    c.fill = PatternFill("solid", fgColor="F2F6FA")
            dv.add(f"J{ri}")
            s.cell(row=ri, column=10).fill = PatternFill("solid", fgColor="FFF2CC")
        s.freeze_panes = "B2"
        s.auto_filter.ref = f"A1:K{len(data) + 1}"
        s.cell(row=len(data) + 3, column=1,
               value="Legend: yellow Status cells are for you to fill (Pass / Fail / Blocked / Not run).").font = \
            Font(name=font, size=9, italic=True)
    wb.save(out)
    simple = [x for x in rows if x[1] == "Simple"]
    full = [x for x in rows if x[1] == "Full"]
    stretch = [x for x in rows if x[1] == "Stretch"]
    print(f"simple {len(simple)} tests/{sum(x[7] for x in simple)} cases; full {len(full)}/{sum(x[7] for x in full)};"
          f" stretch {len(stretch)}/{sum(x[7] for x in stretch)}")


if __name__ == "__main__":
    main(sys.argv[1])
