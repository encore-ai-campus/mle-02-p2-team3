import csv
import json
from pathlib import Path

import pytest

from payment_card.file_pipeline.graph.cypher_export import export_cypher


def _write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _inputs(folder, count=1):
    folder.mkdir(parents=True)
    _write_csv(folder / "pf_load_runs.csv", ["run_id", "input_folder_name", "model_name", "started_at", "node_count", "edge_count"], [])
    _write_csv(folder / "pf_nodes.csv", ["id", "node_type", "props", "chunk_id", "run_id"], [
        {"id": f"n{i}", "node_type": "Benefit", "props": json.dumps({"name": "O'Reilly\\path\nnext", "active": True, "tags": ["a"], "nested": {"k": 1}}, ensure_ascii=False), "chunk_id": "c", "run_id": "r"}
        for i in range(count)
    ])
    _write_csv(folder / "pf_edges.csv", ["id", "source_id", "target_id", "edge_type", "run_id"], [])
    _write_csv(folder / "pf_evidence.csv", ["node_id", "edge_id", "doc_sha256", "page_no", "start_pos", "end_pos", "quote_status"], [])


def test_exports_escaped_flat_properties_and_nested_json(tmp_path):
    source = tmp_path / "csv"
    _inputs(source)
    output = tmp_path / "load.cypher"
    export_cypher(source, output)
    text = output.read_text(encoding="utf-8")
    assert "O\\'Reilly\\\\path\\nnext" in text
    assert "active: true" in text
    assert 'props_json: \'{"tags":["a"],"nested":{"k":1}}\'' in text
    assert "quote" not in text.lower()
    assert ":PfBenefit" in text
    assert "CREATE CONSTRAINT pf_benefit_id_unique" in text
    assert ":Benefit" not in text


def test_batches_are_split_at_500_rows(tmp_path):
    source = tmp_path / "csv"
    _inputs(source, count=501)
    output = tmp_path / "load.cypher"
    export_cypher(source, output)
    text = output.read_text(encoding="utf-8")
    assert text.count("UNWIND [") == 2
    assert text.count("MERGE (n:PfBenefit") == 2


def test_rejects_output_inside_repository(tmp_path):
    source = tmp_path / "csv"
    _inputs(source)
    repo = Path(__file__).resolve().parents[4]
    with pytest.raises(ValueError, match="저장소 밖"):
        export_cypher(source, repo / "generated.cypher")


def test_rejects_label_injection(tmp_path):
    source = tmp_path / "csv"
    _inputs(source)
    nodes = source / "pf_nodes.csv"
    rows = list(csv.DictReader(nodes.open(encoding="utf-8", newline="")))
    rows[0]["node_type"] = "Benefit) DETACH DELETE n //"
    _write_csv(nodes, list(rows[0]), rows)
    with pytest.raises(ValueError, match="node_type"):
        export_cypher(source, tmp_path / "load.cypher")


def test_readme_and_queries_have_only_scoped_delete_and_prefixed_patterns():
    root = Path(__file__).resolve().parents[1] / "file_pipeline" / "graph" / "cypher"
    readme = (root / "README.md").read_text(encoding="utf-8")
    queries = (root / "queries.cypher").read_text(encoding="utf-8")
    assert "MATCH (n) DETACH DELETE n" not in readme + queries
    assert "MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Pf') DETACH DELETE n" in readme
    assert "MATCH (n)" not in queries
    assert ":Card" not in queries and ":Benefit" not in queries
