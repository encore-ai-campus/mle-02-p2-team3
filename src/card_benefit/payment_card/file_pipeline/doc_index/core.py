"""항목(entry) 목록에서 documents / product_docs 행을 만든다. 카드사 이름을 알지 못한다."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import ORIGIN_RANK, OCR_MIN_CHARS_PER_PAGE


def _folder_card_type(rel_path: str) -> str:
    folder = rel_path.split("/", 1)[0]
    return folder if folder in ("credit", "debit", "common") else "unknown"


def _rank_key(doc: dict) -> tuple:
    board = int(doc["board_date"]) if doc["board_date"].isdigit() else 0
    name = doc["file_path"].rsplit("/", 1)[-1]
    return (ORIGIN_RANK[doc["origin"]], -board, len(name), doc["file_path"])


def build_index(issuer: str, issuer_root: Path, entries: list[dict], measure) -> tuple[list[dict], list[dict], dict]:
    """entries는 어댑터가 만든 항목이고, measure는 measure_pdf와 같은 모양의 함수다.

    같은 파일을 가리키는 항목은 파일 1개로 합치고 상품 연결만 늘린다.
    반환: (documents 행, product_docs 행, 점검 요약)
    """
    by_path: dict[str, list[dict]] = {}
    for entry in entries:
        by_path.setdefault(entry["file_path"], []).append(entry)

    docs: dict[str, dict] = {}
    missing = []
    for path, group in by_path.items():
        first = group[0]
        info = measure(issuer_root / path)
        if not info.get("exists"):
            missing.append(path)
            continue
        reasons = []
        for entry in group:
            reasons.extend(entry.get("review_reasons", []))
        if info.get("error"):
            reasons.append(info["error"])
        manifest_sha = {e["manifest_sha256"] for e in group if e.get("manifest_sha256")}
        if manifest_sha and info["sha256"] not in manifest_sha:
            reasons.append("manifest 해시와 파일 해시가 다름")
        pages, chars = info.get("pages"), info.get("text_chars")
        ocr = bool(pages) and chars is not None and chars / pages < OCR_MIN_CHARS_PER_PAGE
        docs[path] = {
            "issuer": issuer,
            "doc_id": info["sha256"][:16],
            "sha256": info["sha256"],
            "file_path": f"{issuer}_all/{path}",
            "_path": path,
            "card_type": _folder_card_type(path),
            "doc_role": first["doc_role"],
            "canonical": "N",
            "duplicate_of": "",
            "pages": "" if pages is None else pages,
            "text_chars": "" if chars is None else chars,
            "ocr_needed": "Y" if ocr else "N",
            "source_url": first.get("source_url", ""),
            "origin": first["origin"],
            "board_date": first.get("board_date", ""),
            "_reasons": list(dict.fromkeys(reasons)),
            "_products": {e["product_name"] for e in group},
        }

    # 같은 해시의 파일끼리 대표 1개를 고른다.
    groups: dict[str, list[dict]] = {}
    for doc in docs.values():
        groups.setdefault(doc["sha256"], []).append(doc)
    for members in groups.values():
        members.sort(key=_rank_key)
        winner = members[0]
        winner["canonical"] = "Y"
        for other in members[1:]:
            other["duplicate_of"] = winner["file_path"]

    # 공식 상품설명서가 있는 카드의 웹 변환본은 대표에서 뺀다.
    official_products = {
        product
        for doc in docs.values()
        if doc["doc_role"] == "product_guide"
        for product in doc["_products"]
    }
    for doc in docs.values():
        if doc["doc_role"] != "web_capture" or doc["canonical"] != "Y":
            continue
        if doc["_products"] <= official_products:
            doc["canonical"] = "N"
        else:
            doc["_reasons"].append("공식 상품설명서 없이 웹 변환본만 존재")

    # 연결 표: 같은 내용(해시)을 몇 개 상품이 쓰는지에 따라 relation이 갈린다.
    # 공유 문서는 경로가 달라도 해시가 같은 파일로 들어오기도 한다.
    products_by_sha = {
        sha: set().union(*(d["_products"] for d in members)) for sha, members in groups.items()
    }
    product_docs = []
    seen = set()
    for entry in entries:
        doc = docs.get(entry["file_path"])
        if doc is None:
            continue
        key = (entry["product_name"], entry["file_path"])
        if key in seen:
            continue
        seen.add(key)
        role = doc["doc_role"]
        if role in ("product_guide", "web_capture"):
            relation = "shared_guide" if len(products_by_sha[doc["sha256"]]) > 1 else "primary_guide"
        elif role == "brand_service":
            relation = "brand"
        elif role == "terms":
            relation = "terms"
        else:
            relation = role
        product_docs.append({
            "issuer": issuer,
            "product_name": entry["product_name"],
            "product_ids": json.dumps(entry.get("product_ids", {}), ensure_ascii=False, sort_keys=True),
            "card_type": doc["card_type"],
            "doc_id": doc["doc_id"],
            "file_path": doc["file_path"],
            "relation": relation,
        })

    documents = []
    for doc in sorted(docs.values(), key=lambda d: d["file_path"]):
        if doc["doc_role"] == "unclassified":
            doc["_reasons"].append("문서 종류를 규칙으로 판정하지 못함")
        reasons = list(dict.fromkeys(doc["_reasons"]))
        doc["needs_review"] = "Y" if reasons else "N"
        doc["review_reason"] = "; ".join(reasons)
        documents.append({k: v for k, v in doc.items() if not k.startswith("_")})

    summary = {
        "entries": len(entries),
        "files": len(documents),
        "missing_files": missing,
        "ocr_needed": sum(d["ocr_needed"] == "Y" for d in documents),
        "needs_review": sum(d["needs_review"] == "Y" for d in documents),
        "unclassified": sum(d["doc_role"] == "unclassified" for d in documents),
        "duplicate_groups": sum(1 for m in groups.values() if len(m) > 1),
        "bad_canonical_groups": [
            sha for sha, m in groups.items()
            if sum(d["canonical"] == "Y" for d in m) > 1
            or (sum(d["canonical"] == "Y" for d in m) == 0 and not all(d["doc_role"] == "web_capture" for d in m))
        ],
    }
    return documents, product_docs, summary
