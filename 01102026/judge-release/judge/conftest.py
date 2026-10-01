"""Judge fixtures + result recorder (used by grade.py)."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from harness import Api, AppProcess  # noqa: E402

CATEGORIES = {
    "AUTHN": "Login & token issuance (A07, A04)",
    "TOKEN": "Token validation (A07, A08)",
    "RBAC": "Role-based access control (A01)",
    "OBJECT": "Object-level authZ & data scope (A01)",
    "FILTER": "Filtering, sorting & pagination",
    "INPUT": "Input validation & injection (A05)",
    "WORKFLOW": "Business rules & idempotency (A06)",
    "CONFIG": "Security configuration & hardening (A02)",
    "LOGGING": "Security logging & alerting (A09)",
    "RESILIENCE": "Exceptional conditions & NFRs (A10, NFR)",
}
_results = []


def pytest_configure(config):
    config.addinivalue_line("markers", "cat(name): scoring category")


@pytest.fixture(scope="module")
def app(request):
    overrides = getattr(request.module, "APP_ENV_OVERRIDES", {})
    proc = AppProcess(overrides)
    ok = proc.start()
    if not ok:
        log = proc.log_text()[-2000:]
        proc.stop()
        pytest.fail(f"Candidate API did not start (cmd={proc.cfg['start_cmd']!r}). Log tail:\n{log}")
    yield proc
    proc.stop()


@pytest.fixture(scope="module")
def api(app):
    client = Api(app)
    yield client
    client.close()


def pytest_collection_modifyitems(config, items):
    wanted = {c.strip().upper() for c in os.environ.get("JUDGE_CATS", "").split(",") if c.strip()}
    if not wanted:
        return
    keep, drop = [], []
    for it in items:
        (keep if _category(it) in wanted else drop).append(it)
    config.hook.pytest_deselected(items=drop)
    items[:] = keep


def _category(item):
    m = item.get_closest_marker("cat")
    return m.args[0] if m else "UNCATEGORISED"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" or (rep.when == "setup" and rep.outcome != "passed"):
        doc = (item.function.__doc__ or "").strip().splitlines()
        _results.append({
            "nodeid": item.nodeid, "category": _category(item),
            "title": doc[0] if doc else item.name,
            "outcome": "passed" if rep.passed else ("skipped" if rep.skipped else "failed"),
            "message": "" if rep.passed else _reason(rep),
        })


def _reason(rep):
    crash = getattr(getattr(rep, "longrepr", None), "reprcrash", None)
    msg = crash.message if crash is not None else str(rep.longrepr or "")
    return " ".join(msg.replace("AssertionError:", "").split())[:300]


def pytest_sessionfinish(session):
    out = os.environ.get("JUDGE_RESULTS")
    if out:
        Path(out).write_text(json.dumps({"categories": CATEGORIES, "results": _results}, indent=2))
