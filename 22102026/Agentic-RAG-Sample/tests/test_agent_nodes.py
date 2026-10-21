"""Lab 2 · A08-A19: the graph nodes, one at a time."""
import httpx
from langgraph.types import Send
from openai import APIConnectionError

from app.agent.nodes import DEFAULT_DIRECT_REPLY
from app.generation import NOT_FOUND

from .conftest import ev, sub


def boom():
    return APIConnectionError(request=httpx.Request("POST", "http://gateway"))


# ------------------------------------------------------------------ TODO 3 / 4
def test_A08_route_parses_messy_json_and_falls_back_to_simple(fake, nodes):
    cc = fake.chat.completions
    cc.handlers["ROUTE"] = 'Sure!\n```json\n{"route": "complex", "reason": "two documents"}\n```'
    out = nodes.route({"standalone": "q?", "clarifications": 0})
    assert out["route"] == "complex" and out["route_reason"] == "two documents"
    system, user = cc.calls[-1]["messages"][0]["content"], cc.calls[-1]["messages"][1]["content"]
    assert system.startswith("TASK: ROUTE") and "ALREADY_CLARIFIED: no" in user and "q?" in user
    cc.handlers["ROUTE"] = "I think this needs search"
    assert nodes.route({"standalone": "q?"})["route"] == "simple"
    cc.handlers["ROUTE"] = '{"route": "web_search", "reason": "x"}'
    assert nodes.route({"standalone": "q?"})["route"] == "simple"


def test_A09_route_guards_clarify_direct_and_gateway_errors(fake, nodes):
    cc = fake.chat.completions
    cc.handlers["ROUTE"] = '{"route": "clarify", "reason": "vague", "clarify_question": "Which limit?"}'
    assert nodes.route({"standalone": "limit?", "clarifications": 0})["clarify_question"] == "Which limit?"
    again = nodes.route({"standalone": "limit? (hotel)", "clarifications": 1})
    assert again["route"] == "simple" and "ALREADY_CLARIFIED: yes" in cc.calls[-1]["messages"][1]["content"]
    cc.handlers["ROUTE"] = '{"route": "clarify", "reason": "vague"}'
    assert nodes.route({"standalone": "limit?"})["route"] == "simple"   # no question to ask
    cc.handlers["ROUTE"] = '{"route": "direct", "reason": "hi"}'
    d = nodes.route({"standalone": "hi"})
    assert d["route"] == "direct" and d["direct_reply"] == DEFAULT_DIRECT_REPLY
    cc.raise_exc = boom()
    e = nodes.route({"standalone": "q"})
    assert e["route"] == "simple" and e["route_reason"] == "router unavailable"


def test_A10_after_route_maps_routes_to_nodes(nodes):
    assert nodes.after_route({"route": "direct"}) == "direct_answer"
    assert nodes.after_route({"route": "clarify"}) == "clarify"
    assert nodes.after_route({"route": "simple"}) == "plan"
    assert nodes.after_route({"route": "complex"}) == "plan"
    assert nodes.after_route({}) == "plan"


# ------------------------------------------------------------------ TODO 5 / 6
def test_A11_plan_simple_makes_one_search_without_llm(fake, nodes):
    out = nodes.plan({"route": "simple", "standalone": "hotel cap?"})
    assert fake.chat.completions.tasks == []
    assert out["plan"] == out["pending"] == [sub("r1-q1", "hotel cap?")]
    assert out["rounds"] == 0


def test_A12_plan_complex_validates_and_caps_sub_questions(fake, nodes):
    cc = fake.chat.completions
    cc.handlers["PLAN"] = """{"sub_questions": [
        {"question": "per diem in metro cities", "tool": "search"},
        "not a dict",
        {"question": "   ", "tool": "search"},
        {"question": "everything for trainees", "tool": "entity", "entity": "grad trainees"},
        {"question": "Per diem in  METRO cities", "tool": "search"},
        {"question": "unicorn rules", "tool": "entity", "entity": "unicorn"},
        {"question": "fourth valid one", "tool": "magic"}]}"""
    out = nodes.plan({"route": "complex", "standalone": "q"})
    p = out["plan"]
    assert [s["id"] for s in p] == ["r1-q1", "r1-q2", "r1-q3"]                  # capped at 3
    assert p[1]["tool"] == "entity" and p[1]["entity"] == "graduate trainee"    # resolved
    assert p[2] == sub("r1-q3", "unicorn rules")                                # unknown entity -> search
    assert "graduate trainee" in cc.calls[-1]["messages"][0]["content"]          # known entities given to the LLM
    cc.handlers["PLAN"] = "no idea"
    assert nodes.plan({"route": "complex", "standalone": "q"})["plan"] == [sub("r1-q1", "q")]


def test_A13_fan_out_sends_only_new_sub_queries(nodes):
    a, b, c = sub("r1-q1", "a"), sub("r1-q2", "b"), sub("r1-q3", "x", "entity", "HSM")
    out = nodes.fan_out({"pending": [a, b, c], "tried_queries": ["a"]})
    assert all(isinstance(s, Send) and s.node == "retrieve" for s in out)
    assert [s.arg["sub"]["id"] for s in out] == ["r1-q2", "r1-q3"]
    assert nodes.fan_out({"pending": [a], "tried_queries": ["a"]}) == "generate"
    assert nodes.fan_out({"pending": [], "tried_queries": []}) == "generate"
    assert nodes.fan_out({"pending": [c], "tried_queries": ["entity:hsm"]}) == "generate"


# ------------------------------------------------------------------ TODO 7
def test_A14_retrieve_uses_the_chosen_tool_and_falls_back(fake, nodes):
    out = nodes.retrieve({"sub": sub("r1-q2", "trainee rules", "entity", "graduate trainee")})
    assert out["tried_queries"] == ["entity:graduate trainee"]
    assert {e["tool"] for e in out["evidence"]} == {"entity"} and {e["sub_id"] for e in out["evidence"]} == {"r1-q2"}
    assert len({e["source"] for e in out["evidence"]}) >= 4
    fb = nodes.retrieve({"sub": sub("r1-q1", "hotel cap per night", "entity", "unicorn")})
    assert fb["steps"][0]["data"]["tool"] == "search" and fb["evidence"]
    s = nodes.retrieve({"sub": sub("r1-q1", "PAY-E4035 bank file signature")})
    assert 1 <= len(s["evidence"]) <= 5 and s["tried_queries"] == ["pay-e4035 bank file signature"]
    assert any("PAY-E4035" in e["text"] for e in s["evidence"])


# ------------------------------------------------------------------ TODO 8
def test_A15_assess_filters_relevance_and_plans_follow_ups(fake, nodes):
    fake.chat.completions.handlers["ASSESS"] = (
        '{"relevant": [2, 2, 9, 0, "1", true, 3], "sufficient": "false", '
        '"missing": ["Sev-2 response time", "", "already searched", "sev-2   RESPONSE time", "third one", "fourth"]}'
    )
    state = {"standalone": "q", "rounds": 0, "evidence": [ev("a#0"), ev("b#0"), ev("a#0"), ev("c#0")],
             "tried_queries": ["already searched"]}
    out = nodes.assess(state)
    assert out["rounds"] == 1
    assert out["relevant_ids"] == ["b#0", "c#0"]          # 2 and 3 of the DEDUPED list
    assert out["sufficient"] is False
    assert [p["question"] for p in out["pending"]] == ["Sev-2 response time", "third one"]
    assert [p["id"] for p in out["pending"]] == ["r2-q1", "r2-q2"] and out["pending"][0]["round"] == 2


def test_A16_assess_fails_open_and_skips_llm_without_evidence(fake, nodes):
    fake.chat.completions.handlers["ASSESS"] = "the passages look fine to me"
    out = nodes.assess({"standalone": "q", "evidence": [ev("a#0"), ev("b#0")]})
    assert out["relevant_ids"] == ["a#0", "b#0"] and out["sufficient"] is True and out["pending"] == []
    fake.chat.completions.tasks.clear()
    empty = nodes.assess({"standalone": "q", "evidence": [], "rounds": 1})
    assert empty["rounds"] == 2 and empty["relevant_ids"] == [] and fake.chat.completions.tasks == []


def test_A17_after_assess_loops_only_while_useful(nodes):
    p = [sub("r2-q1", "follow up")]
    assert nodes.after_assess({"sufficient": True, "rounds": 1, "pending": p}) == "generate"
    assert nodes.after_assess({"sufficient": False, "rounds": 2, "pending": p}) == "generate"   # max_rounds = 2
    assert nodes.after_assess({"sufficient": False, "rounds": 1, "pending": []}) == "generate"
    out = nodes.after_assess({"sufficient": False, "rounds": 1, "pending": p, "tried_queries": []})
    assert [s.arg["sub"]["id"] for s in out] == ["r2-q1"]


# ------------------------------------------------------------------ TODO 9
def test_A18_generate_uses_relevant_evidence_calculator_and_feedback(fake, nodes):
    cc = fake.chat.completions
    cc.handlers["ANSWER"] = "Per diem INR 2,000 [1], hotel INR 7,500 [2]. Total <calc>3*2000 + 3*7500</calc> INR [2][5]. Bad <calc>import os</calc>."
    state = {"standalone": "Pune trip?", "relevant_ids": ["c#0", "a#0"], "feedback": "mention the hotel cap",
             "evidence": [ev("a#0", "per diem 2000"), ev("b#0", "irrelevant"), ev("c#0", "hotel 7500")]}
    out = nodes.generate(state)
    assert "28500" in out["answer"] and "import os (could not compute)" in out["answer"]
    assert out["calculations"][0] == {"expr": "3*2000 + 3*7500", "value": "28500"}
    assert out["used_ids"] == ["a#0", "c#0"]           # evidence order, irrelevant b#0 dropped
    assert out["citations"] == [1, 2]                  # [5] ignored
    user = cc.calls[-1]["messages"][1]["content"]
    assert "[1] (source: a)" in user and "irrelevant" not in user and "Fix it: mention the hotel cap" in user
    cc.tasks.clear()
    none = nodes.generate({"standalone": "q", "relevant_ids": [], "evidence": [ev("a#0")]})
    assert none["answer"] == NOT_FOUND and cc.tasks == []
    many = nodes.generate({"standalone": "q", "relevant_ids": [f"d#{i}" for i in range(12)],
                           "evidence": [ev(f"d#{i}", "x") for i in range(12)]})
    assert len(many["used_ids"]) == 8                   # max_context_chunks


# ------------------------------------------------------------------ TODO 10
def test_A19_check_retries_once_then_stops(fake, nodes):
    cc = fake.chat.completions
    cc.handlers["CHECK"] = '{"grounded": false, "complete": true, "problem": "INR 9,000 is not in the passages"}'
    base = {"standalone": "q", "answer": "It is INR 9,000 [1].", "used_ids": ["a#0"], "evidence": [ev("a#0", "INR 7,500")]}
    first = nodes.check({**base, "regenerations": 0})
    assert first["check"]["retry"] is True and first["regenerations"] == 1 and "9,000" in first["feedback"]
    assert nodes.after_check(first) == "generate"
    second = nodes.check({**base, "regenerations": 1})
    assert second["check"]["retry"] is False and second["regenerations"] == 1
    assert nodes.after_check(second) == "finalize"
    cc.tasks.clear()
    assert nodes.check({**base, "answer": NOT_FOUND})["check"]["skipped"] is True
    nodes.cfg.check_answer = False
    assert nodes.check(base)["check"]["skipped"] is True and cc.tasks == []
