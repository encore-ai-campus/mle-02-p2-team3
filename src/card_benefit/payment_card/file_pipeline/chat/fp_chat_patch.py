"""Opt-in adapter for running the team's GraphRAG chatbot against fp_chat views."""
from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
import os
import re
import sys
import time

try:
    from .db_pool import PoolQueryRunner
except ImportError:  # Script-style imports from this directory.
    from db_pool import PoolQueryRunner

_CHATBOT_DIR = Path(__file__).resolve().parents[4] / "graphrag_chatbot"
_CURRENT_QUESTION: ContextVar[str] = ContextVar("fp_chat_question", default="")
_ORIGINAL_ANSWER = None
_ORIGINAL_LIST_ENTITIES = None
_ORIGINAL_ANALYZE = None
_ORIGINAL_EXPLORE = None
_ORIGINAL_GENERATE_STREAM = None
_ORIGINAL_ANSWER_SYSTEM = None
_ORIGINAL_RUN_QUERY = None
_POOL_RUN_QUERY = None
_PATCHED_DB = None
_ANSWER_CAPTURE: ContextVar[dict | None] = ContextVar("fp_chat_answer_capture", default=None)


def _load_modules():
    if str(_CHATBOT_DIR) not in sys.path:
        sys.path.insert(0, str(_CHATBOT_DIR))
    # db.py calls load_dotenv() at import time. Keep this adapter environment-only:
    # importing it must not open a repository .env file.
    import dotenv  # noqa: PLC0415
    original_loader = dotenv.load_dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False
    try:
        import db  # noqa: PLC0415
    finally:
        dotenv.load_dotenv = original_loader
    return db


def _rank_candidates(rows, tokens, limit: int = 500) -> dict:
    """일치 행을 질문 단어 일치 점수 순으로 정렬해 최대 limit 개를 돌려준다(결정적)."""
    import math  # noqa: PLC0415
    names: dict[str, str] = {}
    for row in rows:
        names.setdefault(row["name"], row["label"])
    lowered = [token.lower() for token in tokens]
    df = {t: sum(1 for name in names if t in name.lower()) for t in lowered}
    priority = {"Card": 0, "Benefit": 1}
    scored = []
    for name, label in names.items():
        low = name.lower()
        score = sum(min(len(t), 6) / math.log(2 + df[t]) for t in lowered if df[t] and t in low)
        scored.append((-score, priority.get(label, 2), name, label))
    scored.sort()
    return {name: {"name": name, "label": label} for _, _, name, label in scored[:limit]}


def _make_list_entities(db, schema: str):
    def list_entities(question: str | None = None) -> list[dict]:
        q = question if question is not None else _CURRENT_QUESTION.get()
        tokens = []
        for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", q):
            if token not in tokens:
                tokens.append(token)
            if len(tokens) == 12:
                break
        patterns = [f"%{token}%" for token in tokens]
        # 이름순 상한(300)은 흔한 단어가 많이 걸리면 정답 엔티티를 잘라 낸다(실측: 하나카드 12문항 중 3개).
        # 일치한 행을 모두 가져와(안전 상한 5000) 파이썬에서 단어 중요도(흔한 단어는 낮게) 순으로 정렬한다.
        matched = db.run_query(
            f"select name, label from {schema}.nodes "
            "where label <> 'Document' and name ilike any(%(patterns)s) limit 5000",
            {"patterns": patterns},
        ) if patterns else []
        unique = _rank_candidates(matched, tokens)
        remaining = max(0, 500 - len(unique))
        if remaining:
            supplemental = db.run_query(
                f"select name, label from {schema}.nodes "
                "where label in ('Card', 'Benefit') and not (name = any(%(names)s)) "
                "order by case label when 'Card' then 0 else 1 end, name limit %(limit)s",
                {"names": list(unique), "limit": remaining},
            )
            for row in supplemental:
                unique.setdefault(row["name"], {"name": row["name"], "label": row["label"]})
                if len(unique) == 500:
                    break
        return list(unique.values())
    return list_entities


def apply(schema: str = "fp_chat"):
    """Configure chatbot db/rag modules for a validated PostgreSQL schema (opt in)."""
    if not isinstance(schema, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ValueError("schema must match [A-Za-z_][A-Za-z0-9_]*")
    global _ORIGINAL_ANSWER, _ORIGINAL_LIST_ENTITIES, _ORIGINAL_ANALYZE
    global _ORIGINAL_EXPLORE, _ORIGINAL_GENERATE_STREAM, _ORIGINAL_ANSWER_SYSTEM
    global _ORIGINAL_RUN_QUERY, _POOL_RUN_QUERY, _PATCHED_DB
    db = _load_modules()
    if _ORIGINAL_RUN_QUERY is None:
        _ORIGINAL_RUN_QUERY = db.run_query
        _PATCHED_DB = db
    if __import__("os").environ.get("FP_DB_POOL") == "0":
        db.run_query = _ORIGINAL_RUN_QUERY
    else:
        if _POOL_RUN_QUERY is None:
            _POOL_RUN_QUERY = PoolQueryRunner(_ORIGINAL_RUN_QUERY)
        db.run_query = _POOL_RUN_QUERY
    db.SCHEMA = schema
    db.NODES = f"{schema}.nodes"
    db.EDGES = f"{schema}.edges"
    import rag  # noqa: PLC0415
    importlib = __import__("importlib")
    importlib.reload(rag)  # REACH_SQL is constructed from db constants at import time.
    if _ORIGINAL_ANSWER is None:
        _ORIGINAL_ANSWER = rag.answer
        _ORIGINAL_LIST_ENTITIES = getattr(rag, "list_entities", None)
        _ORIGINAL_ANALYZE = getattr(rag, "analyze", None)
        _ORIGINAL_EXPLORE = getattr(rag, "explore", None)
        _ORIGINAL_GENERATE_STREAM = getattr(rag, "generate_stream", None)
    if _ORIGINAL_ANSWER_SYSTEM is None:
        _ORIGINAL_ANSWER_SYSTEM = getattr(rag, "ANSWER_SYSTEM", "")
    try:
        from .answer_format import ANSWER_SYSTEM_V2
    except ImportError:
        from answer_format import ANSWER_SYSTEM_V2
    legacy = os.environ.get("FP_ANSWER_FORMAT", "v2").strip().lower() == "legacy"
    rag.ANSWER_SYSTEM = _ORIGINAL_ANSWER_SYSTEM if legacy else ANSWER_SYSTEM_V2
    rag.list_entities = _make_list_entities(db, schema)
    original_answer = _ORIGINAL_ANSWER
    original_analyze = _ORIGINAL_ANALYZE
    original_explore = _ORIGINAL_EXPLORE
    original_generate_stream = _ORIGINAL_GENERATE_STREAM

    def list_entities(question: str | None = None):
        capture = _ANSWER_CAPTURE.get()
        started = time.perf_counter()
        try:
            return _make_list_entities(db, schema)(question)
        finally:
            if capture is not None:
                capture["latency_ms"]["entities_db"] = (time.perf_counter() - started) * 1000

    rag.list_entities = list_entities

    def answer(question: str, history=None):
        token = _CURRENT_QUESTION.set(question)
        if not os.environ.get("FP_QA_LOG"):
            try:
                return original_answer(question, history)
            finally:
                _CURRENT_QUESTION.reset(token)
        capture = {"latency_ms": {}, "selected_entities": []}
        capture_token = _ANSWER_CAPTURE.set(capture)
        usage_module = sys.modules.get("llm")
        usage_before = None
        try:
            if usage_module is not None and callable(getattr(usage_module, "usage_totals", None)):
                usage_before = usage_module.usage_totals()
        except Exception:
            usage_before = None
        started = time.perf_counter()
        try:
            result = original_answer(question, history)
            if not isinstance(result, dict):
                return result
            result["selected_entities"] = list(capture["selected_entities"])
            try:
                from . import answer_eval, qa_log
            except ImportError:
                import answer_eval
                import qa_log
            stages = capture["latency_ms"]
            stages["total"] = (time.perf_counter() - started) * 1000
            usage_after = None
            try:
                if usage_module is not None and callable(getattr(usage_module, "usage_totals", None)):
                    usage_after = usage_module.usage_totals()
            except Exception:
                usage_after = None
            usage = None
            if usage_after is not None:
                usage = {key: max(0, usage_after.get(key, 0) - (usage_before or {}).get(key, 0))
                         for key in ("prompt_tokens", "completion_tokens", "cost_usd")}
            subgraph = result.get("subgraph") or {}
            refs, evidence_error = [], None
            fp_ids = [str(n.get("props", {}).get("fp_id")) for n in subgraph.get("nodes", [])
                      if n.get("props", {}).get("fp_id") and not str(n["props"]["fp_id"]).startswith("doc:")]
            try:
                # 문서 전체 근거를 끌어오지 않는다: 검색된 노드에 직접 붙은 근거와,
                # 양 끝 노드가 모두 검색된 엣지의 근거만 출처로 기록한다.
                refs = db.run_query(
                    "select distinct e.node_id, e.edge_id, e.doc_sha256, e.page_no, e.start_pos, e.end_pos, e.quote_status "
                    "from public.fp_evidence e left join public.fp_edges edge on edge.id = e.edge_id "
                    "where e.node_id = any(%(node_ids)s) "
                    "or (edge.source_id = any(%(node_ids)s) and edge.target_id = any(%(node_ids)s)) "
                    "order by e.doc_sha256, e.page_no, e.start_pos limit 1000",
                    {"node_ids": fp_ids},
                )
            except Exception:
                refs, evidence_error = [], "source_refs_query_error"
            try:
                record = qa_log.build_record(
                    question=question, answer=result.get("answer", ""), result=result,
                    model=getattr(usage_module, "MODEL", None), usage=usage,
                    latency_ms=stages, answer_format_version="legacy" if legacy else "v2",
                    graph_schema=schema, source_refs=refs, evidence_error=evidence_error,
                    app_version=os.environ.get("GIT_COMMIT") or os.environ.get("GITHUB_SHA"),
                )
                record["refusal"] = answer_eval._refusal(str(result.get("answer", "")))
                qa_log.write_record(record)
            except Exception:
                print("FP_QA_LOG_ERROR:record_error", file=sys.stderr)
            return result
        finally:
            _ANSWER_CAPTURE.reset(capture_token)
            _CURRENT_QUESTION.reset(token)

    rag.answer = answer
    if original_analyze is not None:
        def analyze(question: str, entities: list[dict]):
            # app.py calls analyze(question, list_entities()) directly; retrieve keyword candidates there too.
            if not _CURRENT_QUESTION.get():
                entities = rag.list_entities(question)
            capture = _ANSWER_CAPTURE.get()
            started = time.perf_counter()
            value = original_analyze(question, entities)
            if capture is not None:
                capture["latency_ms"]["analyze_llm"] = (time.perf_counter() - started) * 1000
                capture["selected_entities"] = list(getattr(value, "entities", []) or [])
            return value
        rag.analyze = analyze

    def explore(analysis):
        capture = _ANSWER_CAPTURE.get()
        started = time.perf_counter()
        try:
            return original_explore(analysis)
        finally:
            if capture is not None:
                capture["latency_ms"]["explore_db"] = (time.perf_counter() - started) * 1000

    def generate_stream(question, sub, history=None):
        capture = _ANSWER_CAPTURE.get()
        started = time.perf_counter()
        first = None
        try:
            for chunk in original_generate_stream(question, sub, history):
                if first is None:
                    first = time.perf_counter()
                    if capture is not None:
                        capture["latency_ms"]["first_token"] = (first - started) * 1000
                yield chunk
        finally:
            if capture is not None and first is None:
                capture["latency_ms"]["first_token"] = None

    rag.explore = explore
    rag.generate_stream = generate_stream
    return rag


def restore():
    """Restore the team DB query function and the original answer prompt."""
    global _PATCHED_DB
    if _PATCHED_DB is not None and _ORIGINAL_RUN_QUERY is not None:
        _PATCHED_DB.run_query = _ORIGINAL_RUN_QUERY
    rag = sys.modules.get("rag")
    if rag is not None and _ORIGINAL_ANSWER_SYSTEM is not None:
        rag.ANSWER_SYSTEM = _ORIGINAL_ANSWER_SYSTEM
