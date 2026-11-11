import csv
import json
from pathlib import Path

import pytest

from payment_card.file_pipeline.graph import export


def test_csv_write_failure_does_not_publish_partial_output(tmp_path, monkeypatch):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    out = tmp_path / "csv"
    out.mkdir()
    original = export._write_csv
    def fail_second(path, columns, rows):
        if path.name == "fp_nodes.csv":
            raise OSError("synthetic write failure")
        original(path, columns, rows)
    monkeypatch.setattr(export, "_write_csv", fail_second)
    with pytest.raises(OSError, match="synthetic"):
        export.export_files(result_dir, chunk_dir, index_dir, "test", out)
    assert list(out.iterdir()) == []


def test_export_rejects_nonempty_output_without_overwriting(tmp_path):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    out = tmp_path / "csv"
    out.mkdir()
    (out / "existing.txt").write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export.export_files(result_dir, chunk_dir, index_dir, "test", out)
    assert (out / "existing.txt").read_text(encoding="utf-8") == "existing"
    assert not (out / "fp_nodes.csv").exists()


def _write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path):
    result_dir, chunk_dir, index_dir = (tmp_path / n for n in ("results", "chunks", "index"))
    for p in (result_dir, chunk_dir, index_dir):
        p.mkdir()
    chunk = {"doc_id": "doc1", "doc_sha256": "a" * 64, "chunks": [{"chunk_id": "c1", "page_no": 1}]}
    (chunk_dir / "doc.chunks.json").write_text(json.dumps(chunk), encoding="utf-8")
    extraction = {
        "benefits": [{"id": "b1", "name": "혜택", "method": "DISCOUNT", "rate": "5%", "amount": None,
                       "evidence": [{"text": "문구", "location": {"doc_sha256": "a"*64, "page_no": 1, "start_pos": 2, "end_pos": 3}},
                                    {"text": "누락", "location": None}]}],
        "conditions": [{"id": "cnd1", "text": "조건", "kind": "OTHER", "min_amount": None, "evidence": [{"text": "모호", "location": {"doc_sha256": "a"*64, "page_no": 1, "start_pos": 4, "end_pos": 5}}]}],
        "limits": [], "targets": [],
        "relations": [{"source": "b1", "target": "cnd1", "type": "HAS_CONDITION", "evidence": [{"text": "관계", "location": {"doc_sha256": "a"*64, "page_no": 1, "start_pos": 6, "end_pos": 7}}]}],
    }
    result = {"chunk_id": "c1", "doc_sha256": "a"*64, "page_no": 1, "extraction": extraction,
              "failures": [{"code": "quote_location_ambiguous", "path": "conditions[0].evidence[0]"}]}
    (result_dir / "c1.result.json").write_text(json.dumps(result), encoding="utf-8")
    _write_csv(index_dir / "product_docs.csv", ["issuer", "product_name", "product_ids", "card_type", "doc_id"],
               [{"issuer": "hana", "product_name": "카드", "product_ids": '{"CD_ID":"123"}', "card_type": "credit", "doc_id": "doc1"},
                {"issuer": "hana", "product_name": "카드", "product_ids": '{"CD_ID":"123"}', "card_type": "credit", "doc_id": "doc1"}])
    _write_csv(index_dir / "documents.csv", ["doc_id", "sha256"], [{"doc_id": "doc1", "sha256": "a"*64}])
    return result_dir, chunk_dir, index_dir


@pytest.mark.parametrize("kind", ["corrupt", "duplicate"])
def test_export_rejects_invalid_chunk_inputs_before_writing(tmp_path, kind):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    extra = chunk_dir / "extra.json"
    extra.write_text("{" if kind == "corrupt" else json.dumps({
        "doc_id": "other", "chunks": [{"chunk_id": "c1", "page_no": 2}]
    }), encoding="utf-8")
    out = tmp_path / "csv"
    out.mkdir()
    existing = out / "fp_nodes.csv"
    existing.write_text("preserved", encoding="utf-8")
    with pytest.raises(ValueError):
        export.export_files(result_dir, chunk_dir, index_dir, "test", out)
    assert existing.read_text(encoding="utf-8") == "preserved"


@pytest.mark.parametrize("kind", ["missing", "page", "document"])
def test_export_rejects_result_without_matching_chunk_before_writing(tmp_path, kind):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    path = result_dir / "c1.result.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    if kind == "missing":
        result["chunk_id"] = "missing"
    elif kind == "page":
        result["page_no"] = 2
    else:
        result["doc_sha256"] = "b" * 64
    path.write_text(json.dumps(result), encoding="utf-8")
    out = tmp_path / "csv"
    out.mkdir()
    existing = out / "fp_nodes.csv"
    existing.write_text("preserved", encoding="utf-8")
    with pytest.raises(ValueError, match="청크"):
        export.export_files(result_dir, chunk_dir, index_dir, "test", out)
    assert existing.read_text(encoding="utf-8") == "preserved"


def test_export_remaps_relations_evidence_and_deduplicates_cards(tmp_path):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    out = tmp_path / "csv"
    summary = export.export_files(result_dir, chunk_dir, index_dir, "test", out, run_id="run1")
    nodes = list(csv.DictReader((out / "fp_nodes.csv").open(encoding="utf-8")))
    edges = list(csv.DictReader((out / "fp_edges.csv").open(encoding="utf-8")))
    evidence = list(csv.DictReader((out / "fp_evidence.csv").open(encoding="utf-8")))
    assert {n["id"] for n in nodes} >= {"c1:b1", "c1:cnd1", "card:hana:123"}
    assert any(e["source_id"] == "c1:b1" and e["target_id"] == "c1:cnd1" for e in edges)
    assert sum(e["node_type"] == "Card" for e in nodes) == 1
    assert sum(e["edge_type"] == "OFFERS" for e in edges) == 1
    assert {e["quote_status"] for e in evidence} == {"located", "ambiguous", "missing"}
    assert all(not (e["page_no"] or e["start_pos"] or e["end_pos"]) for e in evidence if e["quote_status"] != "located")
    assert all(e["page_no"] and e["start_pos"] and e["end_pos"] for e in evidence if e["quote_status"] == "located")
    assert summary["invalid_rows"] == {}


def test_shared_document_creates_offers_for_each_indexed_card_without_edge_evidence(tmp_path):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    _write_csv(index_dir / "product_docs.csv",
               ["issuer", "product_name", "product_ids", "card_type", "doc_id"],
               [{"issuer": "hana", "product_name": name, "product_ids": json.dumps({"CD_ID": key}),
                 "card_type": "credit", "doc_id": "doc1"} for name, key in [("카드 A", "A"), ("카드 B", "B")]])
    out = tmp_path / "csv"
    export.export_files(result_dir, chunk_dir, index_dir, "test", out, run_id="run1")
    with (out / "fp_edges.csv").open(encoding="utf-8") as stream:
        offers = [row for row in csv.DictReader(stream) if row["edge_type"] == "OFFERS"]
    with (out / "fp_evidence.csv").open(encoding="utf-8") as stream:
        evidence_edge_ids = {row["edge_id"] for row in csv.DictReader(stream) if row["edge_id"]}
    assert {(edge["source_id"], edge["target_id"]) for edge in offers} == {
        ("card:hana:A", "c1:b1"), ("card:hana:B", "c1:b1")}
    assert not ({edge["id"] for edge in offers} & evidence_edge_ids)




def test_export_excludes_bad_rows_and_repository_output(tmp_path):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    bad = json.loads((result_dir / "c1.result.json").read_text())
    bad["extraction"]["relations"].append({"source": "cnd1", "target": "b1", "type": "HAS_CONDITION", "evidence": []})
    bad["extraction"]["benefits"][0]["evidence"].append({"text": "검증 오류", "location": {"doc_sha256": "a"*64, "page_no": 1, "start_pos": 0, "end_pos": 1}})
    (result_dir / "c1.result.json").write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        export.export_files(result_dir, chunk_dir, index_dir, "test", Path(__file__).resolve().parents[4] / "bad")
    summary = export.export_files(result_dir, chunk_dir, index_dir, "test", tmp_path / "out", run_id="run1")
    assert summary["invalid_rows"].get("invalid_endpoint_types", 0) == 1
    assert summary["invalid_rows"].get("invalid_evidence_position", 0) == 1


@pytest.mark.parametrize(
    ("product_ids", "expected_card", "expected_offers", "expected_missing"),
    [
        ('{"CD_ID":"hana-1"}', "card:hana:hana-1", 1, 0),
        ('{"product_code":"woori-1"}', "card:woori:woori-1", 1, 0),
        ('{}', None, 0, 1),
        ('{"CD_ID":"hana-first","product_code":"woori-second"}', "card:hana:hana-first", 1, 0),
    ],
)
def test_export_uses_supported_product_keys_in_priority_order(
    tmp_path, product_ids, expected_card, expected_offers, expected_missing
):
    result_dir, chunk_dir, index_dir = _fixture(tmp_path)
    _write_csv(
        index_dir / "product_docs.csv",
        ["issuer", "product_name", "product_ids", "card_type", "doc_id"],
        [{"issuer": expected_card.split(":")[1] if expected_card else "hana", "product_name": "카드", "product_ids": product_ids, "card_type": "credit", "doc_id": "doc1"}],
    )

    out = tmp_path / "csv"
    summary = export.export_files(result_dir, chunk_dir, index_dir, "test", out, run_id="run1")
    nodes = list(csv.DictReader((out / "fp_nodes.csv").open(encoding="utf-8")))
    edges = list(csv.DictReader((out / "fp_edges.csv").open(encoding="utf-8")))

    card_ids = {n["id"] for n in nodes if n["node_type"] == "Card"}
    assert card_ids == ({expected_card} if expected_card else set())
    assert sum(e["edge_type"] == "OFFERS" for e in edges) == expected_offers
    assert summary["invalid_rows"].get("missing_product_key", 0) == expected_missing
