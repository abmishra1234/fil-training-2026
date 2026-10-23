"""
Group D - Confidential deal codenames: case-insensitive match against a list kept in a
config file. Your DEFAULT config must list "Project Falcon" and "Project Monsoon".   JT17 - JT22
"""
from __future__ import annotations

import adapter
import pytest

P = adapter.make_passage
V = adapter.result_view


def codename_count(text: str, gw=None) -> int:
    r = V((gw or adapter).check("q", [P("t#0", text)]))
    return r["findings"].get(adapter.TYPE_CODENAME, 0)


@pytest.mark.parametrize("text", [
    "project falcon kickoff is on Monday",
    "PROJECT MONSOON budget approved",
    "Project Falcon's timeline slipped",
    "Notes on Project Monsoon.",
    "pRoJeCt FaLcOn",
], ids=["lower", "upper", "possessive", "end-of-sentence", "mixed-case"])
def test_JT17_default_codenames_case_insensitive(text):
    """Default config codenames match in any case and next to punctuation."""
    assert codename_count(text) == 1


@pytest.mark.parametrize("text", [
    "Project Falconry is a hobby club",
    "The falcon project is not the codename",
    "Monsoon season leave rules",
    "Project Falcone is a different word",
], ids=["Falconry", "reordered", "monsoon-only", "Falcone"])
def test_JT18_whole_phrase_only(text):
    """Only the whole phrase counts: no substring hits, no single-word hits."""
    r = V(adapter.check("q", [P("w#0", text)]))
    assert r["decision"] == "ALLOW" and r["dropped"] == []


def test_JT19_codenames_come_from_the_config_file(tmp_path):
    """A different config file -> a different list. Proves the list is loaded, not hard-coded."""
    cfg = adapter.write_codename_config(tmp_path, ["Project Kestrel", "Orion Deal"])
    gw = adapter.make_gateway(codenames_path=cfg)
    assert codename_count("project kestrel go-live", gw) == 1
    assert codename_count("ORION DEAL term sheet", gw) == 1
    assert codename_count("Project Falcon status", gw) == 0, "Project Falcon is not in THIS config"
    # the other secret types still work with a custom codename config
    r = V(gw.check("q", [P("o#0", "key sk-test-9f8e7d6c5b4a3f2e1d0c")]))
    assert r["dropped"] == ["o#0"]


def test_JT20_config_entries_are_literal_text_not_regex(tmp_path):
    """Regex characters in a codename are matched literally and never crash the gateway."""
    cfg = adapter.write_codename_config(tmp_path, ["Deal (Alpha)+", "Project X.9", "Q[3]*Merger"])
    gw = adapter.make_gateway(codenames_path=cfg)
    assert codename_count("the deal (alpha)+ was signed", gw) == 1
    assert codename_count("Project X.9 launches", gw) == 1
    assert codename_count("q[3]*merger closed", gw) == 1
    assert codename_count("Deal Alpha was signed", gw) == 0
    assert codename_count("Project X19 launches", gw) == 0, "'.' must not act as a wildcard"
    assert codename_count("Q3Merger", gw) == 0


@pytest.mark.parametrize("text", ["Project\nFalcon", "Project  Monsoon", "Project\tFalcon", "Project \n Monsoon"],
                         ids=["newline", "double-space", "tab", "space-newline-space"])
def test_JT21_codename_split_by_whitespace_or_line_break(text):
    """Chunked text wraps lines: a codename split by any whitespace is still the codename."""
    assert codename_count(f"Update: {text} moves to phase 2") == 1


def test_JT22_mixed_types_exact_counts():
    """Counts are per type and per occurrence: {CODENAME: 3, CREDENTIAL: 1}."""
    text = "Project Falcon update: Project Monsoon depends on PROJECT FALCON. Ops api_key=abc123XYZ987"
    r = V(adapter.check("q", [P("m#0", text)]))
    f = {k: v for k, v in r["findings"].items() if v}
    assert f == {adapter.TYPE_CODENAME: 3, adapter.TYPE_CREDENTIAL: 1}
    assert r["decision"] == "BLOCK_CONTEXT" and r["dropped"] == ["m#0"]
