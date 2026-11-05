"""Answer evaluation stays dry-run by default; --mode retrieval runs LLM-free graph retrieval."""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
CHATBOT_DIR = HERE.parents[3] / "graphrag_chatbot"
REPO_ROOT = HERE.parents[5]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
from common.query_logger import QueryLogger


def _safe_tmp(path):
    path = Path(path).expanduser().resolve()
    if Path("/tmp").resolve() not in path.parents or path == REPO_ROOT or REPO_ROOT in path.parents:
        raise ValueError("출력은 저장소 밖 /tmp 아래만 허용됩니다.")
    return path


def metrics(records):
    search_total = search_hit = answer_total = answer_hit = source_hit = 0
    durations = []
    for rec in records:
        result = rec["result"]
        expected = rec["question"].get("expected", [])
        expected_names = rec["question"].get("expected_node_names", [])
        node_names = {n.get("name", "") for n in result.get("subgraph", {}).get("nodes", [])}
        if expected_names:
            search_total += len(expected_names)
            search_hit += sum(name in node_names for name in expected_names)
        answer = result.get("answer", "")
        answer_total += len(expected)
        answer_hit += sum(str(value) in answer for value in expected)
        source_hit += bool(result.get("sources"))
        durations.append(rec.get("elapsed_seconds", 0.0))
    count = len(records)
    return {
        "retrieval_hit_rate": search_hit / search_total if search_total else 0.0,
        "retrieval_hits": search_hit, "retrieval_expected": search_total,
        "answer_inclusion_rate": answer_hit / answer_total if answer_total else 0.0,
        "answer_included": answer_hit, "answer_expected": answer_total,
        "source_rate": source_hit / count if count else 0.0,
        "average_seconds": sum(durations) / len(durations) if durations else 0.0,
        "questions": count,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("questions", help="eval_questions JSON (under /tmp)")
    parser.add_argument("--mode", choices=("answer", "retrieval"), default="answer")
    parser.add_argument("--source", choices=("csv", "db"), default="csv")
    parser.add_argument("--seed-mode", choices=("contains", "fuzzy", "oracle"), default="contains")
    parser.add_argument("--seed-threshold", type=float, default=0.15)
    parser.add_argument("--hops", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--csv-dir", action="append", default=[])
    parser.add_argument("--summary", default="/tmp/fp-retrieval-summary.json")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output", default="/tmp/fp-chat-eval.jsonl")
    args = parser.parse_args(argv)
    qpath = Path(args.questions).expanduser().resolve()
    if Path("/tmp").resolve() not in qpath.parents or REPO_ROOT in qpath.parents:
        raise ValueError("질문 JSON은 /tmp 아래에 있어야 합니다.")
    if args.mode == "retrieval":
        from retrieval_eval import main as retrieval_main
        argv = [str(qpath), "--source", args.source, "--seed-mode", args.seed_mode, "--seed-threshold", str(args.seed_threshold), "--hops", str(args.hops), "--output", args.output, "--summary", args.summary]
        if args.execute: argv.append("--execute")
        for folder in args.csv_dir: argv.extend(["--csv-dir", folder])
        return retrieval_main(argv)
    payload = json.loads(qpath.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])[:max(0, args.limit)]
    estimate = len(questions) * 2  # 상한 추정: 분석 호출 + 답변 생성 호출
    if not args.execute:
        print(json.dumps({"mode": "dry-run", "question_count": len(questions), "llm_call_estimate": estimate, "ids": [q.get("id") for q in questions]}, ensure_ascii=False))
        return 0
    if not os.environ.get("DB_URL") or not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("answer mode requires DB_URL and ANTHROPIC_API_KEY; use --mode retrieval for LLM-free evaluation.")

    if str(CHATBOT_DIR) not in sys.path:
        sys.path.insert(0, str(CHATBOT_DIR))
    from fp_chat_patch import apply
    rag = apply()
    logger = logging.getLogger("fp_chat_eval")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    # QueryLogger는 이벤트 필드만 기록한다. 명시적으로 쿼리 파라미터 상세 로깅을 끈다.
    query_logger = QueryLogger(logger, log_mode="none", sensitive_keys=("question", "params", "password", "api_key"))
    out = _safe_tmp(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    records = []
    with out.open("w", encoding="utf-8") as stream:
        for q in questions:
            start = time.perf_counter()
            result = rag.answer(q["question"])
            elapsed = time.perf_counter() - start
            rec = {"id": q.get("id"), "question": q, "result": result, "elapsed_seconds": elapsed}
            records.append(rec)
            stream.write(json.dumps(rec, ensure_ascii=False) + "\n")
            query_logger.log_summary("fp_chat_eval_question", "rag.answer", question_id=q.get("id"), elapsed_seconds=round(elapsed, 6), row_count=len(result.get("subgraph", {}).get("nodes", [])))
    print(json.dumps({"output": str(out), "metrics": metrics(records)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
