"""Opt-in adapter for running the team's GraphRAG chatbot against fp_chat views."""
from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
import re
import sys

try:
    from .db_pool import PoolQueryRunner
except ImportError:  # Script-style imports from this directory.
    from db_pool import PoolQueryRunner

_CHATBOT_DIR = Path(__file__).resolve().parents[4] / "graphrag_chatbot"
_CURRENT_QUESTION: ContextVar[str] = ContextVar("fp_chat_question", default="")
_ORIGINAL_ANSWER = None
_ORIGINAL_LIST_ENTITIES = None
_ORIGINAL_ANALYZE = None
_ORIGINAL_RUN_QUERY = None
_POOL_RUN_QUERY = None
_PATCHED_DB = None


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
    rag.list_entities = _make_list_entities(db, schema)
    original_answer = _ORIGINAL_ANSWER
    original_analyze = _ORIGINAL_ANALYZE

    def answer(question: str, history=None):
        token = _CURRENT_QUESTION.set(question)
        try:
            return original_answer(question, history)
        finally:
            _CURRENT_QUESTION.reset(token)

    rag.answer = answer
    if original_analyze is not None:
        def analyze(question: str, entities: list[dict]):
            # app.py calls analyze(question, list_entities()) directly; retrieve keyword candidates there too.
            if not _CURRENT_QUESTION.get():
                entities = rag.list_entities(question)
            return original_analyze(question, entities)
        rag.analyze = analyze
    return rag


def restore():
    """Restore the team DB query function after an opt-in patch."""
    global _PATCHED_DB
    if _PATCHED_DB is not None and _ORIGINAL_RUN_QUERY is not None:
        _PATCHED_DB.run_query = _ORIGINAL_RUN_QUERY
