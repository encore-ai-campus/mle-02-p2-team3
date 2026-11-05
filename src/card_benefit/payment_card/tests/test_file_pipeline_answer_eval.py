import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest

CHAT = Path(__file__).resolve().parents[1] / "file_pipeline" / "chat"


@pytest.fixture(autouse=True)
def _restore_chatbot_modules():
    """이 파일의 테스트가 sys.modules 에 남기는 db/rag/llm 을 원상 복구해 다른 테스트(예: seed_matcher 의 미임포트 확인)로 새지 않게 한다."""
    names = ("db", "rag", "llm")
    before = {name: sys.modules.get(name) for name in names}
    yield
    for name, module in before.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module

def load(name):
    spec = importlib.util.spec_from_file_location(f"answer_eval_test_{name}", CHAT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_openai_patch_injects_llm_module_without_anthropic(monkeypatch):
    import importlib.util
    patch = load("openai_llm_patch")
    monkeypatch.delitem(sys.modules, "llm", raising=False)
    fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="ok"))], usage=types.SimpleNamespace(prompt_tokens=3, completion_tokens=2)))))
    llm = patch.install(client=fake)
    assert sys.modules["llm"] is llm
    assert llm.complete("s", "u") == "ok"
    assert patch.usage_totals() == {"prompt_tokens": 3, "completion_tokens": 2, "cost_usd": 0.0000013}
    monkeypatch.setitem(sys.modules, "db", types.SimpleNamespace(NODES="fp_chat.nodes", EDGES="fp_chat.edges"))
    monkeypatch.setitem(sys.modules, "timing", types.ModuleType("timing"))
    spec = importlib.util.spec_from_file_location("rag_without_anthropic", CHAT.parents[3] / "graphrag_chatbot" / "rag.py")
    rag = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = rag
    spec.loader.exec_module(rag)
    assert callable(rag.answer)


def test_openai_patch_request_arguments_and_stream_fallback(monkeypatch):
    patch = load("openai_llm_patch")
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        if kwargs.get("stream"):
            raise RuntimeError("unsupported stream options")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="whole"))], usage=types.SimpleNamespace(prompt_tokens=1, completion_tokens=1))
    fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    llm = patch.install(client=fake)
    assert list(llm.stream("s", [{"role": "user", "content": "q"}])) == ["whole"]
    assert "max_completion_tokens" in calls[0] and "max_tokens" not in calls[0]
    assert "temperature" not in calls[0]
    assert calls[0]["stream_options"] == {"include_usage": True}


def test_answer_metrics_normalize_refusal_and_classification():
    answer_eval = load("answer_eval")
    assert answer_eval.judge_answer(
        {"expected": ["₩20,000", "월", "해외 가맹점"], "seed_entities": ["가나다 카드"]},
        {"answer": "모르겠습니다. 월 20000원", "sources": [], "subgraph": {"nodes": [{"name": "가나다 카드", "props": {"amount": 20000, "target": "해외 가맹점"}}]}},
        ["가나다 카드"],
    )["classification"] == "search_hit_answer_miss"
    refused = answer_eval.judge_answer({"expected": ["월"], "seed_entities": ["없음"]}, {"answer": "관련 정보가 없습니다", "sources": [], "subgraph": {"nodes": []}}, [])
    assert refused["refusal"] is True
    assert refused["classification"] == "search_miss"
    no_answer = answer_eval.judge_answer({"no_answer": True}, {"answer": "정보가 없습니다", "subgraph": {"nodes": []}}, [])
    assert no_answer["no_answer_success"] is True and no_answer["expected_values"] == 0


def test_dry_run_does_not_touch_db_or_openai(tmp_path, monkeypatch, capsys):
    run = load("run_eval")
    qfile = Path("/tmp/fp-answer-eval-dry-test.json")
    qfile.write_text(json.dumps({"questions": [{"id": "q1", "question": "synthetic", "expected": ["x"]}]}))
    try:
        assert run.main([str(qfile), "--mode", "answer", "--llm", "openai"]) == 0
        assert json.loads(capsys.readouterr().out)["question_count"] == 1
    finally:
        qfile.unlink(missing_ok=True)


def test_output_repo_guard():
    answer_eval = load("answer_eval")
    try:
        answer_eval.safe_tmp(Path(__file__))
    except ValueError:
        return
    assert False, "repository output path was accepted"


def test_openai_cost_limit_stops_and_redacts_key(monkeypatch, capsys):
    patch = load("openai_llm_patch")
    key = "synthetic-secret-never-print"
    monkeypatch.setenv("OPENAI_API_KEY", key)
    made = []
    def create(**kwargs):
        made.append(kwargs)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="safe"))], usage=types.SimpleNamespace(prompt_tokens=1000000, completion_tokens=0))
    fake = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
    patch.reset_usage()
    patch.install(client=fake, max_cost_usd=0.01)
    try:
        sys.modules["llm"].complete("s", "u")
    except patch.CostLimitExceeded:
        pass
    assert len(made) == 1
    assert key not in capsys.readouterr().out
    assert key not in json.dumps(patch.usage_totals())


def test_execute_with_fake_chatbot_db_and_openai_modules(tmp_path, monkeypatch, capsys):
    import argparse
    answer_eval = load("answer_eval")
    monkeypatch.setenv("DB_URL", "synthetic-db-url")
    secret = "synthetic-openai-key-never-write"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    qfile = Path("/tmp/fp-answer-execute-fake.json")
    output = Path("/tmp/fp-answer-execute-fake.jsonl")
    summary = Path("/tmp/fp-answer-execute-fake-summary.json")
    qfile.write_text(json.dumps({"questions": [{"id": "s1", "type": "synthetic", "question": "synthetic?", "seed_entities": ["synthetic node"], "expected": ["20,000"]}]}))
    fake_db = types.SimpleNamespace(run_query=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fake DB should not query")))
    monkeypatch.setitem(sys.modules, "db", fake_db)
    class Analysis:
        entities = ["synthetic node"]
        hops = 1
    rag = types.SimpleNamespace()
    rag.analyze = lambda question, entities: Analysis()
    rag.explore = lambda analysis: {"nodes": [{"id": "1", "name": "synthetic node", "label": "Limit", "props": {"amount": 20000}}], "edges": [], "seeds": ["1"]}
    rag.answer = lambda question: {"answer": "20,000 won", "sources": [{"title": "synthetic"}], "subgraph": rag.explore(rag.analyze(question, []))}
    monkeypatch.setitem(sys.modules, "fp_chat_patch", types.SimpleNamespace(apply=lambda schema: rag))
    fake_llm_patch = types.ModuleType("openai_llm_patch")
    fake_llm_patch.CostLimitExceeded = type("CostLimitExceeded", (BaseException,), {})
    fake_llm_patch.install = lambda **kwargs: None
    fake_llm_patch.reset_usage = lambda: None
    fake_llm_patch.usage_totals = lambda: {"prompt_tokens": 7, "completion_tokens": 3, "cost_usd": 0.0000022}
    monkeypatch.setitem(sys.modules, "openai_llm_patch", fake_llm_patch)
    args = argparse.Namespace(questions=str(qfile), limit=1, output=str(output), summary=str(summary),
                              execute=True, llm="openai", max_cost_usd=0.10, sleep=0.0, hops=1)
    assert answer_eval.run(args) == 0
    row = json.loads(output.read_text().splitlines()[0])
    assert row["status"] == "ok" and row["selected_seed_names"] == ["synthetic node"]
    assert row["expected_values_in_answer"] == 1 and row["prompt_tokens"] == 7
    assert row["retrieved_node_ids"] == ["1"]
    stdout = capsys.readouterr().out
    assert "synthetic?" not in stdout
    assert secret not in stdout and secret not in output.read_text()
    qfile.unlink(missing_ok=True)
    output.unlink(missing_ok=True)
    summary.unlink(missing_ok=True)
