"""judge_tests/conftest.py - shared fixtures. Do not edit (edit adapter.py instead)."""
from __future__ import annotations

import contextlib
import io
import logging
import statistics
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import fakes  # noqa: E402

QUERY_BLOCKED_REPLY = "Your request contains restricted content and was not processed."
CONTEXT_BLOCKED_REPLY = "I could not find this in the approved sources."


# ---------------------------------------------------------------- fake LLM
@pytest.fixture
def fake_llm(monkeypatch):
    """Every chat / embedding request of the app goes to an offline recorder."""
    return fakes.install(monkeypatch)


# ---------------------------------------------------------------- logs + stdout capture
class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@contextlib.contextmanager
def capture_everything():
    """Capture ALL log records (root + non-propagating loggers, DEBUG level) and stdout/stderr."""
    handler = _ListHandler()
    touched = []
    root = logging.getLogger()
    old_root_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    for name, lg in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(lg, logging.Logger):
            touched.append((lg, lg.level, lg.disabled))
            lg.setLevel(logging.DEBUG)
            lg.disabled = False
            if not lg.propagate:
                lg.addHandler(handler)
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            yield handler, out, err
    finally:
        root.removeHandler(handler)
        root.setLevel(old_root_level)
        for lg, level, disabled in touched:
            lg.setLevel(level)
            lg.disabled = disabled
            if handler in lg.handlers:
                lg.removeHandler(handler)


def log_text(handler: _ListHandler) -> str:
    parts = []
    for r in handler.records:
        try:
            parts.append(r.getMessage())
        except Exception:  # noqa: BLE001
            parts.append(str(r.msg))
        parts.append(repr(r.args))
        if r.exc_info:
            parts.append(logging.Formatter().formatException(r.exc_info))
        if r.exc_text:
            parts.append(r.exc_text)
    return "\n".join(parts)


# ---------------------------------------------------------------- timing
def median_ms(fn, runs: int = 40, warmup: int = 5) -> float:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1000)
    return statistics.median(samples)


# ---------------------------------------------------------------- RAG app on a tiny synthetic corpus
CLEAN_DOCS = {
    "p1_visitors.md": "# Parking policy\n## Visitors\nVisitors park in bay B near reception. Facilities issues day permits.\n",
    "p2_staff.md": "# Parking policy\n## Staff\nStaff parking opens at 7 am. Electric vehicles use the green bays on level 2.\n",
}
SECRET_DOC = {
    "p3_contractors.md": "# Parking policy\n## Contractors\nContractor parking for Project Falcon uses gate 4. "
                         "Gate controller password=Winter2026! and badge key AKIA4EXAMPLE7KEY9XYZ.\n",
}
ALL_SECRET_DOCS = {
    "s1_cards.md": "# Parking policy\n## Fines\nParking fines are charged to card 4111 1111 1111 1111 on file.\n",
    "s2_keys.md": "# Parking policy\n## Barrier API\nThe barrier API uses key sk-test-9f8e7d6c5b4a3f2e1d0c for ticket sync.\n",
    "s3_deal.md": "# Parking policy\n## New site\nThe new site parking is part of Project Monsoon and opens in May.\n",
}
CLEAN_PASSAGE_MARKERS = ["bay B near reception", "green bays on level 2"]
SECRET_PASSAGE_MARKERS = ["gate 4", "ticket sync", "opens in May", "on file"]


def make_cfg(docs_dir: Path):
    from app.config import RagConfig

    return RagConfig(docs_dir=docs_dir, chunk_size=500, chunk_overlap=60, basic_k=5, mqr_num_queries=3,
                     mqr_k=5, mqr_include_original=True, rrf_k=60, final_k=5, max_context_chars=6000)


@pytest.fixture
def rag_factory(tmp_path, fake_llm):
    import adapter

    def build(docs: dict[str, str], gateway=None):
        d = tmp_path / f"docs_{len(list(tmp_path.iterdir()))}"
        d.mkdir()
        for name, text in docs.items():
            (d / name).write_text(text, encoding="utf-8")
        svc = adapter.make_rag_service(make_cfg(d), None, gateway=gateway)
        svc.reindex()
        fake_llm.reset()  # count only what happens per question
        return svc

    return build
