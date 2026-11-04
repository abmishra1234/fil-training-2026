"""Public contract tests. Your solution must pass these unchanged. Hidden tests use other fixtures."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_ALERT_KEYS = {
    "alert_id",
    "cve_id",
    "asset_id",
    "service",
    "component",
    "installed_version",
    "fixed_version",
    "risk_score",
    "priority",
    "sla_hours",
    "owner",
    "summary",
    "remediation",
    "evidence",
}


@pytest.fixture(scope="module")
def outdir(tmp_path_factory):
    out = tmp_path_factory.mktemp("out")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "counterstrike",
            "run",
            "--data",
            str(ROOT / "data"),
            "--out",
            str(out),
        ],
        check=True,
        cwd=ROOT,
    )
    return out


def test_output_files_exist(outdir):
    for name in ("alerts.json", "needs_human.json", "run_report.json"):
        assert (outdir / name).exists(), name


def test_alert_schema(outdir):
    for alert in json.loads((outdir / "alerts.json").read_text()):
        assert REQUIRED_ALERT_KEYS <= alert.keys()
        assert alert["priority"] in {"P1", "P2", "P3", "P4"}
        assert alert["evidence"], "every alert must carry evidence"


def test_alerts_match_gold(outdir):
    gold = json.loads((ROOT / "data" / "gold" / "expected_alerts.json").read_text())
    got = {
        (a["cve_id"], a["asset_id"]): a["priority"]
        for a in json.loads((outdir / "alerts.json").read_text())
    }
    want = {(g["cve_id"], g["asset_id"]): g["priority"] for g in gold["alerts"]}
    assert got == want


def test_unclear_advisory_routed_to_human(outdir):
    ids = {h["advisory_id"] for h in json.loads((outdir / "needs_human.json").read_text())}
    assert "CVE-2099-0008" in ids
