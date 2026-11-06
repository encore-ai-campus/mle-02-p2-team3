"""Repeat fp_chat retrieval and report entity and subgraph stability."""
from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path
import statistics
import sys
import time
import unicodedata
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[5]


def safe_tmp(path: str | Path) -> Path:
    """Resolve an output path and allow writes only below /tmp and outside this repo."""
    resolved = Path(path).expanduser().resolve()
    tmp = Path("/tmp").resolve()
    if resolved == ROOT or ROOT in resolved.parents or tmp not in resolved.parents:
        raise ValueError("출력은 저장소 밖 /tmp 아래만 허용됩니다.")
    return resolved


def _normal(value: Any) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKC", str(value)).casefold() if ch.isalnum())


def _entity_combo(record: dict) -> tuple[str, ...]:
    entities = record.get("selected_entities", []) or []
    return tuple(sorted(_normal(item) for item in entities))


def _node_ids(record: dict) -> set[str]:
    return {str(item) for item in (record.get("node_ids") or [])}


def _benefit_combos(record: dict) -> set[tuple[str, str]]:
    out = set()
    for benefit in record.get("benefits", []) or []:
        name = _normal(benefit.get("name", ""))
        rate = _normal(benefit.get("rate", ""))
        out.add((name, rate))
    return out


def aggregate_question(records: Iterable[dict]) -> dict[str, Any]:
    """Compute stability measures for one question's repeated retrieval records."""
    rows = list(records)
    entity_combos = {_entity_combo(row) for row in rows}
    node_sets = [_node_ids(row) for row in rows]
    pairwise = []
    for left, right in itertools.combinations(node_sets, 2):
        union = left | right
        pairwise.append(len(left & right) / len(union) if union else 1.0)
    common = set.intersection(*node_sets) if node_sets else set()
    all_nodes = set.union(*node_sets) if node_sets else set()
    benefit_sets = [_benefit_combos(row) for row in rows]
    return {
        "repeat_count": len(rows),
        "distinct_entity_selections": len(entity_combos),
        "mean_pairwise_node_jaccard": statistics.fmean(pairwise) if pairwise else 1.0,
        "common_node_fraction": len(common) / len(all_nodes) if all_nodes else 1.0,
        "nodes_in_some_repeats_only": len(all_nodes - common),
        "benefit_value_sets_differ": bool(benefit_sets) and any(item != benefit_sets[0] for item in benefit_sets[1:]),
    }


def aggregate_records(records: Iterable[dict]) -> list[dict[str, Any]]:
    """Group JSONL records by question id and attach pure per-question metrics."""
    grouped: dict[str, list[dict]] = {}
    for record in records:
        key = str(record.get("question_id", record.get("question_index", "")))
        grouped.setdefault(key, []).append(record)
    results = []
    for question_id, rows in grouped.items():
        results.append({"question_id": question_id, **aggregate_question(rows)})
    return results


def aggregate_all(records: Iterable[dict]) -> dict[str, Any]:
    """Return question metrics plus the total count with differing benefit-value sets."""
    questions = aggregate_records(records)
    return {
        "questions": questions,
        "questions_with_benefit_value_differences": sum(row["benefit_value_sets_differ"] for row in questions),
    }


def _short(value: Any, limit: int = 40) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit]


def _benefit_rows(nodes: list[dict]) -> list[dict]:
    result = []
    for node in nodes:
        if node.get("label") != "Benefit":
            continue
        props = node.get("props") or {}
        result.append({
            "name": _short(node.get("name", props.get("name", ""))),
            "rate": props.get("rate"),
            "amount": props.get("amount"),
            "page_number": next((props.get(key) for key in ("page_no", "page_number", "page") if props.get(key) is not None), None),
        })
    return result


def run_repeated(questions: list[dict], repeat: int, rag: Any, output: str | Path) -> int:
    """Run list_entities -> analyze -> explore; answer generation is never invoked."""
    out = safe_tmp(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    question_context = None
    try:
        from fp_chat_patch import _CURRENT_QUESTION  # installed adapter's context avoids duplicate lookup
        question_context = _CURRENT_QUESTION
    except (ImportError, AttributeError):
        pass
    with out.open("w", encoding="utf-8") as stream:
        for question_index, item in enumerate(questions):
            question = str(item["question"])
            question_id = str(item.get("id", question_index))
            for repeat_number in range(1, repeat + 1):
                started = time.perf_counter()
                token = question_context.set(question) if question_context is not None else None
                try:
                    entities = rag.list_entities(question)
                    analysis = rag.analyze(question, entities)
                    subgraph = rag.explore(analysis) or {}
                finally:
                    if token is not None:
                        question_context.reset(token)
                nodes = list(subgraph.get("nodes") or [])
                record = {
                    "question_id": question_id,
                    "question_index": question_index,
                    "repeat": repeat_number,
                    "selected_entities": list(getattr(analysis, "entities", []) or []),
                    "subgraph_node_count": len(nodes),
                    "node_ids": [str(node.get("id")) for node in nodes if node.get("id") is not None],
                    "benefits": _benefit_rows(nodes),
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                }
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
    return 0


def _load_questions(path: str | Path) -> list[dict]:
    content = Path(path).expanduser().read_text(encoding="utf-8")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return [{"id": index, "question": line.strip()} for index, line in enumerate(content.splitlines()) if line.strip()]
    if not isinstance(payload, list):
        raise ValueError("질문 JSON 최상위 값은 배열이어야 합니다.")
    rows = []
    for index, item in enumerate(payload):
        if isinstance(item, str):
            rows.append({"id": index, "question": item})
        elif isinstance(item, dict) and isinstance(item.get("question"), str):
            rows.append({**item, "id": item.get("id", index)})
        else:
            raise ValueError(f"질문 배열의 {index}번 항목은 문자열 또는 question 필드가 필요합니다.")
    return rows


def _install_runtime() -> Any:
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("FP_CHAT_ENV_FILE") or ROOT / ".env", override=False)
    if not os.environ.get("DB_URL"):
        for name in ("FP_DATABASE_URL", "DB_URI"):
            if os.environ.get(name):
                os.environ["DB_URL"] = os.environ[name]
                break
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("DB_URL"):
        print("OPENAI_API_KEY와 DB_URL이 필요합니다. DB_URL은 FP_DATABASE_URL 또는 DB_URI에서 가져올 수 있습니다.")
        return None

    chat_dir = str(Path(__file__).resolve().parent)
    if chat_dir not in sys.path:
        sys.path.insert(0, chat_dir)

    from openai_llm_patch import install
    from fp_chat_patch import apply

    install()
    return apply("fp_chat")


def _print_summary(path: str | Path) -> int:
    records = [json.loads(line) for line in Path(path).expanduser().read_text(encoding="utf-8").splitlines() if line.strip()]
    aggregate = aggregate_all(records)
    summary = aggregate["questions"]
    print("question_id\trepeats\tentity_selections\tmean_node_jaccard\tcommon_node_fraction\tpartial_only_nodes\tbenefit_values_differ")
    for row in summary:
        print("\t".join(str(row[key]) for key in ("question_id", "repeat_count", "distinct_entity_selections", "mean_pairwise_node_jaccard", "common_node_fraction", "nodes_in_some_repeats_only", "benefit_value_sets_differ")))
    print(f"questions_with_benefit_value_differences\t{aggregate['questions_with_benefit_value_differences']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repeat fp_chat retrieval and measure subgraph stability (no answer generation).")
    subparsers = parser.add_subparsers(dest="command")
    summary_parser = subparsers.add_parser("summarize", help="Summarize a retrieval JSONL file")
    summary_parser.add_argument("--input", required=True, help="Input JSONL")
    parser.add_argument("--questions", help="Question JSON array or UTF-8 file with one question per line")
    parser.add_argument("--repeat", type=int, default=5, help="Retrieval repeats per question (default: 5)")
    parser.add_argument("--output", help="JSONL output path under /tmp")
    args = parser.parse_args(argv)
    if args.command == "summarize":
        return _print_summary(args.input)
    if not args.questions or not args.output:
        parser.error("--questions and --output are required")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    questions = _load_questions(args.questions)
    rag = _install_runtime()
    if rag is None:
        return 1
    return run_repeated(questions, args.repeat, rag, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
