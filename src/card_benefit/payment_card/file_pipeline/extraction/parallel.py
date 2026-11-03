"""Bounded concurrent chunk execution with retries and privacy-safe progress."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import time
from typing import Any, Callable

from .runner import run_chunk


def process_chunks(chunks: list[dict], doc_sha256: str, llm_call: Callable[[str], str],
                   workers: int = 1, retries: int = 2,
                   progress: Callable[[int, int], None] | None = None,
                   on_result: Callable[[int, dict[str, Any]], None] | None = None) -> list[dict[str, Any]]:
    """Process chunks concurrently, preserving input order and recording exhausted failures."""
    workers = max(1, min(16, workers))
    if retries < 0:
        raise ValueError("retries must be non-negative")

    def execute(chunk):
        for attempt in range(retries + 1):
            try:
                result = run_chunk(chunk, doc_sha256, llm_call)
                if not any(f.get("code") == "llm_call_failure" for f in result.get("failures", [])):
                    return result
                if attempt == retries:
                    return result
            except Exception as error:
                if attempt < retries:
                    time.sleep(0.25 * (2 ** attempt))
                    continue
                return {"doc_sha256": doc_sha256, "page_no": chunk["page_no"],
                        "chunk_id": chunk.get("chunk_id"), "chunk_length": len(chunk["text"]),
                        "extraction": None, "failures": [{"code": "llm_call_failure",
                        "message": str(error), "exception_type": type(error).__name__}], "notes": []}

    results = [None] * len(chunks)
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(execute, chunk): i for i, chunk in enumerate(chunks)}
        for future in as_completed(futures):
            result = future.result()
            results[futures[future]] = result
            if on_result:
                on_result(futures[future], result)
            done += 1
            if progress:
                progress(done, len(chunks))
    return results


def stderr_progress(done: int, total: int) -> None:
    print(f"{done}/{total}", file=sys.stderr, flush=True)
