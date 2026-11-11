"""청크 JSON 문서를 순회해 추출 결과와 문서별 요약을 파일로 저장한다."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
import hashlib
import fcntl
import functools
import inspect
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import quote
from typing import Any

from .runner import run_chunk
from .parallel import process_chunks, stderr_progress
from .prompt import build_prompt

LLMCall = Callable[[str], str]
_REPO_ROOT = Path(__file__).resolve().parents[5]


def _locked_output(parameter):
    def decorate(function):
        signature = inspect.signature(function)

        @functools.wraps(function)
        def wrapped(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            value = bound.arguments[parameter]
            output = Path(value) if value is not None else Path(tempfile.gettempdir()) / "file_pipeline_extraction"
            output = output.expanduser().resolve()
            if output == _REPO_ROOT or _REPO_ROOT in output.parents:
                raise ValueError("결과 폴더는 저장소 밖에 지정해야 합니다.")
            output.mkdir(parents=True, exist_ok=True)
            with (output / ".file_pipeline.lock").open("a+") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise RuntimeError("결과 폴더가 사용 중입니다.") from None
                return function(*args, **kwargs)
        return wrapped
    return decorate


def _write_json(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _resume_context(llm_call: LLMCall, supplied: dict | None) -> dict | None:
    context = supplied if supplied is not None else getattr(llm_call, "resume_context", None)
    if context is None:
        return None
    if not isinstance(context, dict) or set(context) != {"provider", "model", "temperature"}:
        raise ValueError("resume_context에는 provider, model, temperature만 올바르게 지정해야 합니다.")
    temperature = context["temperature"]
    if (not isinstance(context["provider"], str) or not context["provider"].strip()
            or not isinstance(context["model"], str) or not context["model"].strip()
            or (temperature is not None and (isinstance(temperature, bool)
                or not isinstance(temperature, (int, float)) or not math.isfinite(temperature)))):
        raise ValueError("resume_context에는 provider, model, temperature만 올바르게 지정해야 합니다.")
    return {key: context[key] for key in ("provider", "model", "temperature")}


def _resume_metadata(chunk: dict, doc_sha256: str, context: dict | None) -> dict:
    input_bytes = json.dumps({"doc_sha256": doc_sha256, "chunk": chunk}, ensure_ascii=False,
                             sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    prompt_bytes = build_prompt(chunk).encode("utf-8")
    return {"version": 1, "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
            "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(), "context": context}


def _result_digest(result: dict) -> str:
    content = {key: value for key, value in result.items() if key != "result_sha256"}
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@_locked_output("output_dir")
def run_batch(
    chunk_files: Path | str | Iterable[Path | str],
    llm_call: LLMCall,
    output_dir: Path | str | None = None,
    *,
    resume: bool = True,
    max_chunks: int | None = None,
    chunk_ids: Iterable[str] | None = None,
    workers: int = 1,
    retries: int = 2,
    fail_fast: bool = True,
    resume_context: dict | None = None,
) -> dict[str, Any]:
    """청크 JSON 한 개나 여러 개를 처리하고 요약을 반환한다.

    기본 결과 폴더는 저장소 밖의 시스템 임시 폴더다. 최대 청크 수는
    새로 호출할 청크 수에 적용하며, 이어하기로 재사용한 결과는 세지 않는다.
    chunk_ids가 주어지면 해당 id만 선택한다. 재개에는 청크·프롬프트 지문과
    provider/model/temperature와 저장된 결과 지문이 일치해야 한다. 검증할 수 없는 기존 결과는 보존하고
    오류를 반환한다. 이력이 없는 구형 결과는 새 출력 폴더에서 실행해야 한다.
    호출 함수에 resume_context 속성이 없으면 동명의 인자로 지정할 수 있다. 둘 다 없으면
    새 결과는 만들 수 있지만 해당 결과의 안전한 이어하기는 허용하지 않는다.
    """
    output = Path(output_dir) if output_dir is not None else Path(tempfile.gettempdir()) / "file_pipeline_extraction"
    output = output.expanduser().resolve()
    if output == _REPO_ROOT or _REPO_ROOT in output.parents:
        raise ValueError("결과 폴더는 저장소 밖에 지정해야 합니다.")
    if max_chunks is not None and max_chunks < 0:
        raise ValueError("max_chunks는 0 이상이어야 합니다.")

    if isinstance(chunk_files, (str, Path)):
        paths = [Path(chunk_files)]
    else:
        paths = [Path(path) for path in chunk_files]
    wanted_ids = set(chunk_ids) if chunk_ids is not None else None
    context = _resume_context(llm_call, resume_context)
    output.mkdir(parents=True, exist_ok=True)
    plans = []
    seen_result_paths = set()
    remaining = max_chunks
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        doc_id = str(document["doc_id"])
        doc_sha256 = document["doc_sha256"]
        selected = [chunk for chunk in document["chunks"]
                    if wanted_ids is None or chunk.get("chunk_id") in wanted_ids]
        results = []
        skipped = 0
        pending = []
        quota_unstarted = 0
        for chunk in selected:
            chunk_id = chunk.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError(f"청크 id가 없거나 올바르지 않습니다: {path}")
            result_path = output / f"{quote(chunk_id, safe='._-')}.result.json"
            if result_path in seen_result_paths:
                raise ValueError(f"중복된 청크 결과 경로입니다: {result_path.name}")
            seen_result_paths.add(result_path)
            saved = None
            if resume and result_path.exists():
                try:
                    saved = json.loads(result_path.read_text(encoding="utf-8"))
                    required = {"doc_sha256", "page_no", "chunk_id", "chunk_length",
                                "extraction", "failures", "notes"}
                    if not isinstance(saved, dict) or not required.issubset(saved):
                        raise ValueError("결과 JSON에 필수 필드가 없습니다.")
                    if (not isinstance(saved["failures"], list)
                            or any(not isinstance(f, dict) or not isinstance(f.get("code"), str)
                                   for f in saved["failures"])):
                        raise ValueError("실패 목록 형식이 올바르지 않습니다.")
                    if (not isinstance(saved["notes"], list)
                            or not isinstance(saved["extraction"], (dict, type(None)))
                            or (saved["extraction"] is None and not saved["failures"])):
                        raise ValueError("추출 결과 또는 메모 형식이 올바르지 않습니다.")
                    if (saved["doc_sha256"] != doc_sha256 or saved["page_no"] != chunk["page_no"]
                            or saved["chunk_id"] != chunk_id or saved["chunk_length"] != len(chunk["text"])):
                        raise ValueError("현재 문서 또는 청크와 일치하지 않습니다.")
                    if context is None:
                        raise ValueError("모델 실행 정보를 확인할 수 없습니다.")
                    if saved.get("resume_metadata") != _resume_metadata(chunk, doc_sha256, context):
                        raise ValueError("청크·프롬프트·모델 검증 정보가 없거나 일치하지 않습니다.")
                    if saved.get("result_sha256") != _result_digest(saved):
                        raise ValueError("저장 결과의 내용 검증 정보가 없거나 일치하지 않습니다.")
                except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
                    detail = str(error) if isinstance(error, ValueError) else type(error).__name__
                    raise ValueError(f"기존 결과 {result_path.name}: {detail} 기존 파일을 보존합니다. 새 출력 폴더를 사용하세요.") from None
            # LLM 호출 실패는 일시적 오류일 수 있어 이어하기에서 다시 시도한다.
            if saved is not None and not any(f.get("code") == "llm_call_failure" for f in saved.get("failures", [])):
                result = saved
                skipped += 1
            else:
                if remaining is not None and remaining <= 0:
                    quota_unstarted += 1
                    continue
                if remaining is not None:
                    remaining -= 1
                pending.append((chunk, result_path, _resume_metadata(chunk, doc_sha256, context)))
                continue
            results.append(result)

        plans.append((doc_id, doc_sha256, results, skipped, pending, quota_unstarted))

    documents = []
    for doc_id, doc_sha256, results, skipped, pending, quota_unstarted in plans:

        def save_completed(index, result):
            _, result_path, metadata = pending[index]
            result["resume_metadata"] = metadata
            result["result_sha256"] = _result_digest(result)
            _write_json(result_path, result)

        processed = process_chunks([item[0] for item in pending], doc_sha256, llm_call,
                                   workers=workers, retries=retries, progress=stderr_progress,
                                   on_result=save_completed, fail_fast=fail_fast)
        for result in processed:
            if result is not None:
                results.append(result)

        summary = _summarize(results, skipped)
        summary.update({"fail_fast_stopped": bool(processed.stopped_reason),
                        "stop_reason": processed.stopped_reason,
                        "executed_chunks": processed.started,
                        "unstarted_chunks": quota_unstarted + len(pending) - processed.started})
        summary_path = output / f"{quote(doc_id, safe='._-')}.summary.json"
        _write_json(summary_path, summary)
        documents.append({"doc_id": doc_id, "summary": summary, "summary_path": str(summary_path)})

    return {"documents": documents, "output_dir": str(output)}


@_locked_output("result_dir")
def summarize_batch(
    chunk_files: Path | str | Iterable[Path | str],
    result_dir: Path | str,
    *,
    chunk_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    """기존 청크 결과만 읽어 문서별 요약을 다시 만든다. LLM을 호출하지 않는다."""
    results_path = Path(result_dir).expanduser().resolve()
    if results_path == _REPO_ROOT or _REPO_ROOT in results_path.parents:
        raise ValueError("결과 폴더는 저장소 밖에 지정해야 합니다.")
    results_path.mkdir(parents=True, exist_ok=True)
    if isinstance(chunk_files, (str, Path)):
        paths = [Path(chunk_files)]
    else:
        paths = [Path(path) for path in chunk_files]
    wanted_ids = set(chunk_ids) if chunk_ids is not None else None

    source_documents = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if wanted_ids is not None:
        available_ids = {chunk.get("chunk_id") for _, document in source_documents
                         for chunk in document["chunks"]}
        unknown_ids = sorted(wanted_ids - available_ids)
        if unknown_ids:
            raise ValueError(f"청크 파일에서 찾지 못한 ID가 있습니다: {', '.join(unknown_ids)}")

    documents = []
    for path, document in source_documents:
        doc_id = str(document["doc_id"])
        doc_sha256 = document["doc_sha256"]
        selected = [chunk for chunk in document["chunks"]
                    if wanted_ids is None or chunk.get("chunk_id") in wanted_ids]
        results = []
        missing = 0
        for chunk in selected:
            chunk_id = chunk.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                raise ValueError(f"청크 id가 없거나 올바르지 않습니다: {path}")
            result_path = results_path / f"{quote(chunk_id, safe='._-')}.result.json"
            if not result_path.is_file():
                missing += 1
                continue
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if (not isinstance(result, dict) or result.get("chunk_id") != chunk_id
                    or result.get("doc_sha256") != doc_sha256
                    or result.get("page_no") != chunk.get("page_no")):
                raise ValueError(f"결과가 청크와 일치하지 않습니다: {result_path.name}")
            results.append(result)

        summary = _summarize(results, skipped=0)
        summary["missing_results"] = missing
        summary_path = results_path / f"{quote(doc_id, safe='._-')}.summary.json"
        _write_json(summary_path, summary)
        documents.append({"doc_id": doc_id, "summary": summary, "summary_path": str(summary_path)})

    return {"documents": documents, "output_dir": str(results_path)}


def _summarize(results: list[dict], skipped: int) -> dict[str, Any]:
    """저장된 청크 결과에서 문서 단위 집계를 만든다.

    succeeded는 hard 실패 코드가 전혀 없는 청크 수이며, failed는 hard 실패 코드가
    하나 이상 있는 청크 수다. 위치 실패만 있는 추출 청크는 failed에 유지하고 partial에도
    포함한다. partial은 extraction이 존재하고 실패 코드가 오직 quote_location_failure인
    청크 수다. quote_location_ambiguous는 경고이며 failures_by_code에는 기존처럼 모든
    코드가 포함된다. with_warnings는 경고가 하나 이상 있는 청크 수다.
    """
    failures_by_code: Counter[str] = Counter()
    warnings_by_code: Counter[str] = Counter()
    quote_locations = Counter()
    hard_failure_codes = {
        "json_parse_failure", "schema_validation_failure", "llm_call_failure",
        "empty_result", "quote_location_failure",
    }
    review_codes = {"quote_location_failure", "quote_location_ambiguous"}
    succeeded = failed = partial = review_required = with_warnings = over_4000 = 0
    for result in results:
        failures = result.get("failures", [])
        hard_failures = False
        has_warning = False
        for failure in failures:
            code = failure["code"]
            failures_by_code[code] += 1
            if code == "quote_location_ambiguous":
                warnings_by_code[code] += 1
                has_warning = True
            elif code in hard_failure_codes or code not in review_codes:
                hard_failures = True
        if result.get("extraction") is None or hard_failures:
            failed += 1
        else:
            succeeded += 1
        if has_warning:
            with_warnings += 1
        if any(failure["code"] in review_codes for failure in failures):
            review_required += 1
        if result.get("chunk_length", 0) > 4000:
            over_4000 += 1
        ambiguous_paths = {failure.get("path") for failure in failures
                           if failure.get("code") == "quote_location_ambiguous"}
        extraction = result.get("extraction")
        codes = {failure.get("code") for failure in failures}
        if extraction is not None and "quote_location_failure" in codes and codes == {"quote_location_failure"}:
            partial += 1
        if extraction is None:
            continue
        for group in ("benefits", "conditions", "limits", "targets", "relations"):
            for item_index, item in enumerate(extraction.get(group, [])):
                for quote_index, evidence in enumerate(item.get("evidence", [])):
                    path = f"{group}[{item_index}].evidence[{quote_index}]"
                    if path in ambiguous_paths:
                        quote_locations["ambiguous"] += 1
                    elif evidence.get("location") is None:
                        quote_locations["failure"] += 1
                    else:
                        quote_locations["success"] += 1

    return {
        "chunks": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "partial": partial,
        "with_warnings": with_warnings,
        "review_required": review_required,
        "skipped": skipped,
        "failures_by_code": dict(sorted(failures_by_code.items())),
        "warnings_by_code": dict(sorted(warnings_by_code.items())),
        "quote_locations": {key: quote_locations[key] for key in ("success", "failure", "ambiguous")},
        "over_4000": over_4000,
    }
