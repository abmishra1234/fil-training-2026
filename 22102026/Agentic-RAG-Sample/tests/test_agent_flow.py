"""Lab 2 · A20-A25: the compiled LangGraph end to end (TODO 11, 12) and the API."""
import json

import pytest
from fastapi.testclient import TestClient

from app.llm import RagError


def nodes_run(result):
    return [s["node"] for s in result["steps"]]


def test_A20_direct_route_answers_without_retrieval(fake, agent):
    fake.chat.completions.handlers["ROUTE"] = '{"route": "direct", "reason": "out of scope", "reply": "I only answer NovaPay handbook questions."}'
    r = agent.ask("Write me a Python sort function")
    assert r["answer"] == "I only answer NovaPay handbook questions."
    assert fake.chat.completions.tasks == ["ROUTE"] and r["llm_calls"] == 1
    assert r["evidence_count"] == 0 and r["embedding_calls"] == 0
    assert nodes_run(r) == ["contextualize", "route", "direct_answer", "finalize"]


def test_A21_complex_question_runs_parallel_sub_queries_and_a_second_hop(fake, agent):
    cc = fake.chat.completions
    cc.handlers["ROUTE"] = '{"route": "complex", "reason": "two parts"}'
    cc.handlers["PLAN"] = ('{"sub_questions": [{"question": "PAY-E5000 first response", "tool": "search"},'
                           '{"question": "trainee rules", "tool": "entity", "entity": "graduate trainee"}]}')
    cc.handlers["ASSESS"] = ['{"relevant": [1, 2], "sufficient": false, "missing": ["Sev-2 acknowledgement time"]}',
                             '{"relevant": [1, 2, 3], "sufficient": true, "missing": []}']
    cc.handlers["ANSWER"] = "Follow Sev-2 [1]. Trainees accrue <calc>1.5 * 6</calc> days in six months [2]."
    r = agent.ask("PAY-E5000 fired: what process and what applies to trainees?")
    assert nodes_run(r) == ["contextualize", "route", "plan", "retrieve", "retrieve", "assess",
                            "retrieve", "assess", "generate", "check", "finalize"]
    retrieves = [s for s in r["steps"] if s["node"] == "retrieve"]
    assert {s["data"]["sub_id"] for s in retrieves} == {"r1-q1", "r1-q2", "r2-q1"}   # parallel + follow-up
    assert r["rounds"] == 2 and "9 days" in r["answer"] and r["calculations"][0]["value"] == "9"
    assert cc.tasks == ["ROUTE", "PLAN", "ASSESS", "ASSESS", "ANSWER", "CHECK"]
    assert r["status"] == "done" and r["sources"] and r["citations"] == [1, 2]


def test_A22_loops_are_bounded_even_if_the_llm_never_is_satisfied(fake, agent):
    cc = fake.chat.completions
    counter = {"n": 0}

    def never_enough(system, user):
        counter["n"] += 1
        return json.dumps({"relevant": [1], "sufficient": False, "missing": [f"another angle {counter['n']}"]})

    cc.handlers["ASSESS"] = never_enough
    cc.handlers["CHECK"] = '{"grounded": false, "complete": false, "problem": "still wrong"}'
    r = agent.ask("hotel cap per night?")
    assert r["rounds"] == 2                                   # AGENT_MAX_ROUNDS
    assert nodes_run(r).count("generate") == 2                # 1 + AGENT_MAX_REGENERATIONS
    assert r["regenerations"] == 1 and r["status"] == "done" and r["answer"]


def test_A23_clarify_interrupts_and_resumes_with_the_users_answer(fake, agent):
    cc = fake.chat.completions
    cc.handlers["ROUTE"] = '{"route": "clarify", "reason": "vague", "clarify_question": "Which limit: hotel or per diem?"}'
    r = agent.ask("What is the limit?", "t-clarify")
    assert r["status"] == "needs_clarification" and r["clarify_question"].startswith("Which limit")
    assert r["answer"] == "" and "generate" not in nodes_run(r)
    done = agent.resume("t-clarify", "hotel in Mumbai")           # router still says clarify: must not ask twice
    assert done["status"] == "done" and done["standalone"] == "What is the limit? (hotel in Mumbai)"
    assert nodes_run(done).count("route") == 2 and "clarify" in nodes_run(done)
    with pytest.raises(RagError) as exc:
        agent.resume("t-clarify", "again")
    assert exc.value.status == 409


def test_A24_memory_rewrites_follow_ups_per_thread_and_resets_turn_state(fake, agent):
    cc = fake.chat.completions
    first = agent.ask("How many sick leave days do employees get?", "t-mem")
    assert "CONTEXTUALIZE" not in cc.tasks                       # first message: nothing to rewrite
    cc.handlers["CONTEXTUALIZE"] = "Can sick leave days be carried forward?"
    second = agent.ask("Can they be carried forward?", "t-mem")
    convo = [c for c in cc.calls if c["messages"][0]["content"].startswith("TASK: CONTEXTUALIZE")][-1]["messages"][1]["content"]
    assert "User: How many sick leave days" in convo and "Assistant: " + first["answer"][:20] in convo
    assert second["standalone"] == "Can sick leave days be carried forward?" and second["turns"] == 2
    assert nodes_run(second)[0] == "contextualize" and nodes_run(second).count("finalize") == 1   # steps reset
    cc.tasks.clear()
    other = agent.ask("Can they be carried forward?", "t-other")
    assert "CONTEXTUALIZE" not in cc.tasks and other["turns"] == 1                                  # new thread, no memory


def test_A25_agent_api_chat_stream_resume_and_graph_endpoints(fake):
    from app.main import app

    cc = fake.chat.completions
    with TestClient(app) as client:
        cc.handlers["ROUTE"] = '{"route": "direct", "reason": "hi", "reply": "Hello!"}'
        r = client.post("/api/agent/chat", json={"question": "hi"})
        assert r.status_code == 200 and r.json()["answer"] == "Hello!" and r.json()["thread_id"]

        cc.handlers["ROUTE"] = ['{"route": "clarify", "reason": "vague", "clarify_question": "Which one?"}',
                                '{"route": "simple", "reason": "ok"}']
        with client.stream("POST", "/api/agent/stream", json={"question": "limit?", "thread_id": "api-1"}) as s:
            events = [json.loads(line[6:]) for line in s.iter_lines() if line.startswith("data: ")]
        assert events[0]["type"] == "start" and events[-1]["type"] == "final"
        assert events[-1]["status"] == "needs_clarification" and any(e["type"] == "step" for e in events)
        res = client.post("/api/agent/resume", json={"thread_id": "api-1", "answer": "hotel"})
        assert res.status_code == 200 and res.json()["status"] == "done"
        assert client.post("/api/agent/resume", json={"thread_id": "api-1", "answer": "x"}).status_code == 409

        assert client.post("/api/agent/chat", json={"question": "   "}).status_code == 422
        assert client.post("/api/agent/stream", json={"resume": "x"}).status_code == 422
        assert client.get("/api/graph/entity/graduate%20trainee").json()["entity"] == "graduate trainee"
        assert client.get("/api/graph/entity/unicorn").status_code == 404
        assert "retrieve" in client.get("/api/agent/graph").json()["mermaid"]
