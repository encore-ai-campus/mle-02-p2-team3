import csv
import importlib.util
import json
from pathlib import Path
import sys
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[4]  # 저장소 루트(src/card_benefit/payment_card/tests 기준)
CHAT = ROOT / "src/card_benefit/payment_card/file_pipeline/chat"
spec = importlib.util.spec_from_file_location("fp_eval_questions", CHAT / "eval" / "eval_questions.py")
eq = importlib.util.module_from_spec(spec); sys.modules[spec.name] = eq; spec.loader.exec_module(eq)
spec2 = importlib.util.spec_from_file_location("fp_run_eval", CHAT / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec2); sys.modules[spec2.name] = run_eval; spec2.loader.exec_module(run_eval)
spec3 = importlib.util.spec_from_file_location("fp_patch", CHAT / "fp_chat_patch.py")
patch = importlib.util.module_from_spec(spec3); sys.modules[spec3.name] = patch; spec3.loader.exec_module(patch)


def write_csv(path, cols, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def sample_dir(path, *, duplicate=False):
    path.mkdir()
    ns=[
      {"id":"c1","node_type":"Card","props":json.dumps({"product_name":"가나다 카드"})},
      {"id":"b1","node_type":"Benefit","props":json.dumps({"name":"커피 할인"})},
      {"id":"l1","node_type":"Limit","props":json.dumps({"period":"월","amount":20000})},
      {"id":"t1","node_type":"Target","props":json.dumps({"text":"해외 가맹점"})},
      {"id":"x1","node_type":"Target","props":json.dumps({"text":"상품권 구매"})},
      {"id":"k1","node_type":"Condition","props":json.dumps({"text":"전월 30만원"})},
    ]
    if duplicate: ns.append({"id":"b2","node_type":"Benefit","props":json.dumps({"name":"커피 할인"})})
    write_csv(path/"fp_nodes.csv",["id","node_type","props"],ns)
    es=[{"id":"e1","source_id":"c1","target_id":"b1","edge_type":"OFFERS"},{"id":"e2","source_id":"b1","target_id":"l1","edge_type":"HAS_LIMIT"},{"id":"e3","source_id":"b1","target_id":"t1","edge_type":"APPLIES_TO"},{"id":"e4","source_id":"b1","target_id":"x1","edge_type":"EXCLUDES"},{"id":"e5","source_id":"b1","target_id":"k1","edge_type":"HAS_CONDITION"}]
    write_csv(path/"fp_edges.csv",["id","source_id","target_id","edge_type"],es)
    write_csv(path/"fp_evidence.csv",["node_id","edge_id","doc_sha256","quote_status"],[{"node_id":"b1","edge_id":"","doc_sha256":"a"*64,"quote_status":"located"}])


def test_apply_schema_validation_and_opt_in(monkeypatch):
    import importlib
    import types
    fake_db=types.SimpleNamespace(SCHEMA="graphrag",NODES="graphrag.nodes",EDGES="graphrag.edges",run_query=lambda *a: [])
    fake_rag=types.ModuleType("rag"); fake_rag.answer=lambda *a,**k: {"answer":"", "subgraph":{"nodes":[]}}
    monkeypatch.setattr(patch,"_load_modules",lambda:fake_db)
    monkeypatch.setitem(sys.modules,"rag",fake_rag)
    monkeypatch.setattr(importlib,"reload",lambda module: module)
    assert (fake_db.NODES,fake_db.EDGES)==("graphrag.nodes","graphrag.edges")
    try: patch.apply("bad.schema")
    except ValueError: pass
    else: assert False
    assert patch.apply("fp_chat") is fake_rag
    assert fake_db.NODES=="fp_chat.nodes" and fake_db.EDGES=="fp_chat.edges"


def test_list_entities_two_queries_binding_cap_and_dedupe(monkeypatch):
    calls=[]
    def query(q,p=None):
        calls.append((q,p))
        if len(calls)==1:
            return [{"name":"커피 할인","label":"Benefit"},{"name":"커피 할인","label":"Benefit"}]
        return [{"name":"우리 카드","label":"Card"}]
    fake_db=type("DB",(),{"run_query":staticmethod(query)})
    rows=patch._make_list_entities(fake_db,"fp_chat")("커피 혜택")
    assert [r["name"] for r in rows]==["커피 할인","우리 카드"]
    assert len(calls)==2 and "ilike any(%(patterns)s)" in calls[0][0]
    assert calls[0][1]=={"patterns":["%커피%","%혜택%"]}
    assert "%(limit)s" in calls[1][0] and calls[1][1]["limit"]==499
    assert len(rows)<=500



def test_list_entities_never_exceeds_500():
    seen=[]
    def query(sql, params=None):
        seen.append((sql, params))
        return [{"name":f"Benefit {i}","label":"Benefit"} for i in range(650)]
    fake_db=type("DB",(),{"run_query":staticmethod(query)})
    result=patch._make_list_entities(fake_db,"fp_chat")("Benefit")
    assert len(result)==500 and len(seen)==1

def test_eval_questions_determinism_ambiguity_and_output_guard(tmp_path):
    folder=tmp_path/"csv"; sample_dir(folder)
    a, skipped=eq.generate([folder],per_type=10,seed=17)
    b,_=eq.generate([folder],per_type=10,seed=17)
    assert a==b and len(a)>=6 and all("원문" not in q["question"] for q in a)
    dup=tmp_path/"dup"; sample_dir(dup,duplicate=True)
    _, skipped_dup=eq.generate([dup],per_type=10,seed=17)
    assert skipped_dup["card_benefits"]>0
    try: eq.write_questions([folder],ROOT/"blocked.json")
    except ValueError: pass
    else: assert False


def test_eval_metrics():
    records=[{"question":{"expected":["월","20000"],"expected_node_names":["커피 할인"]},"result":{"answer":"월 20000원","sources":[{}],"subgraph":{"nodes":[{"name":"커피 할인"}]}},"elapsed_seconds":2}]
    m=run_eval.metrics(records)
    assert m["retrieval_hit_rate"]==1 and m["answer_inclusion_rate"]==1 and m["source_rate"]==1 and m["average_seconds"]==2


def test_dry_run_does_not_call_db_or_llm(tmp_path, monkeypatch, capsys):
    qfile=tmp_path/"q.json"; qfile.write_text(json.dumps({"questions":[{"id":"q1","question":"Q","expected":["A"]}]}))
    monkeypatch.setattr(sys,"argv",["run_eval",str(qfile)])
    # outside /tmp rejected; place under /tmp per interface
    qfile=Path("/tmp/fp-dry-run-test.json"); qfile.write_text(json.dumps({"questions":[{"id":"q1","question":"Q","expected":["A"]}]}))
    monkeypatch.setattr(sys,"argv",["run_eval",str(qfile)])
    assert run_eval.main()==0
    out=json.loads(capsys.readouterr().out)
    assert out["mode"]=="dry-run" and out["question_count"]==1 and out["llm_call_estimate"]==2
    qfile.unlink()


def test_rank_candidates_prefers_rare_matching_words_over_name_order():
    """흔한 단어('할인')가 많이 걸려도 드문 단어('소노')까지 맞는 이름이 이름순 잘림에 밀리지 않아야 한다."""
    rows=[{"name":f"가{i} 할인","label":"Benefit"} for i in range(40)]
    rows+= [{"name":"소노 청구할인","label":"Benefit"},{"name":"소노카드","label":"Card"}]
    ranked=patch._rank_candidates(rows,["소노","할인"],limit=5)
    assert "소노 청구할인" in ranked and "소노카드" in ranked
    assert list(patch._rank_candidates(rows,["소노","할인"],limit=5))==list(ranked)  # 결정적
    assert len(patch._rank_candidates(rows,["소노","할인"],limit=500))==42
