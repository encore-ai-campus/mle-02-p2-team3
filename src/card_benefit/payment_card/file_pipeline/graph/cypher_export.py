"""Export graph CSV files as an idempotent, APOC-free Neo4j Browser script."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_LABELS = ("Issuer", "Card", "Benefit", "Condition", "Limit", "Target")
_RELATION_TYPES = ("HAS_CONDITION", "HAS_LIMIT", "APPLIES_TO", "EXCLUDES", "MUTUALLY_EXCLUSIVE", "OFFERS")
_SAFE_TYPE = re.compile(r"^[A-Za-z_]+$")
_BATCH_SIZE = 500


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t") + "'"


def _literal(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return _string(str(value))


def _map_literal(values: dict) -> str:
    return "{" + ", ".join(f"{key}: {_literal(value)}" for key, value in values.items()) + "}"


def _node_props(raw: str) -> dict:
    props = json.loads(raw or "{}")
    if not isinstance(props, dict):
        raise ValueError("pf_nodes.props는 JSON 객체여야 합니다.")
    scalar, complex_values = {}, {}
    for key, value in props.items():
        if value is None or isinstance(value, (str, bool, int, float)):
            scalar[key] = value
        else:
            complex_values[key] = value
    if complex_values:
        scalar["props_json"] = json.dumps(complex_values, ensure_ascii=False, separators=(",", ":"))
    return scalar


def _unwind(rows: list[dict], clause: str) -> list[str]:
    statements = []
    for start in range(0, len(rows), _BATCH_SIZE):
        batch = rows[start:start + _BATCH_SIZE]
        statements.append("UNWIND [" + ",\n  ".join(_map_literal(row) for row in batch) + f"] AS row\n{clause}")
    return statements


def _validated_type(value: str, allowed: tuple[str, ...], kind: str) -> str:
    if not _SAFE_TYPE.fullmatch(value or "") or value not in allowed:
        raise ValueError(f"허용되지 않은 {kind}: {value!r}")
    return value


def build_script(csv_dir: Path) -> tuple[str, dict[str, int]]:
    nodes = _read_rows(csv_dir / "pf_nodes.csv")
    edges = _read_rows(csv_dir / "pf_edges.csv")
    evidence = _read_rows(csv_dir / "pf_evidence.csv")
    lines = ["// Neo4j Browser용 CSV 적재 스크립트. 재실행 가능한 MERGE를 사용합니다."]
    for label in _LABELS:
        lines.append(f"CREATE CONSTRAINT pf_{label.lower()}_id_unique IF NOT EXISTS FOR (n:Pf{label}) REQUIRE n.id IS UNIQUE;")
    lines.append("CREATE CONSTRAINT pf_evidence_id_unique IF NOT EXISTS FOR (e:PfEvidence) REQUIRE e.evidence_id IS UNIQUE;")

    for label in _LABELS:
        label_rows = []
        for row in nodes:
            if _validated_type(row["node_type"], _LABELS, "node_type") != label:
                continue
            props = _node_props(row.get("props", "{}"))
            props.update({"id": row["id"], "run_id": row.get("run_id", ""), "chunk_id": row.get("chunk_id", "")})
            label_rows.append(props)
        lines.extend(_unwind(label_rows, f"MERGE (n:Pf{label} {{id: row.id}})\nSET n += row;"))

    for rel_type in _RELATION_TYPES:
        rel_rows = [row for row in edges if _validated_type(row["edge_type"], _RELATION_TYPES, "edge_type") == rel_type]
        clause = ("MATCH (source {id: row.source_id}), (target {id: row.target_id})\n"
                  "WHERE any(l IN labels(source) WHERE l STARTS WITH 'Pf') AND any(l IN labels(target) WHERE l STARTS WITH 'Pf')\n"
                  f"MERGE (source)-[r:PF_{rel_type} {{id: row.id}}]->(target)\nSET r.run_id = row.run_id;")
        lines.extend(_unwind(rel_rows, clause))

    evidence_rows = []
    for index, row in enumerate(evidence):
        values = {"evidence_id": f"evidence-{index + 1}", "doc_sha256": row["doc_sha256"],
                  "page_no": int(row["page_no"]) if row.get("page_no") else None,
                  "start_pos": int(row["start_pos"]) if row.get("start_pos") else None,
                  "end_pos": int(row["end_pos"]) if row.get("end_pos") else None,
                  "quote_status": row["quote_status"]}
        if row.get("edge_id"):
            values["edge_id"] = row["edge_id"]
        evidence_rows.append(values)
    lines.append("// 관계 자체에는 Evidence 노드를 연결할 수 없어 edge 근거에는 edge_id를 저장합니다.")
    evidence_clause = "MERGE (e:PfEvidence {evidence_id: row.evidence_id})\nSET e += row\nWITH e, row\nOPTIONAL MATCH (n {id: row.node_id}) WHERE any(l IN labels(n) WHERE l STARTS WITH 'Pf')\nFOREACH (_ IN CASE WHEN row.node_id IS NULL OR n IS NULL THEN [] ELSE [1] END | MERGE (n)-[:PF_HAS_EVIDENCE]->(e));"
    # Node and edge evidence share one representation; node_id is optional and edge_id stays on Evidence.
    # Write node-backed evidence separately so edge-backed evidence never needs a placeholder node id.
    for index, row in enumerate(evidence):
        values = evidence_rows[index]
        node_id = row.get("node_id") or ""
        if node_id:
            values["node_id"] = node_id
    # Null out node_id where absent; the optional match safely skips edge evidence.
    lines.extend(_unwind(evidence_rows, evidence_clause))
    counts = {"nodes": len(nodes), "edges": len(edges), "evidence": len(evidence)}
    return "\n\n".join(lines) + "\n", counts


def export_cypher(csv_dir: str | Path, output: str | Path) -> dict[str, int]:
    csv_dir, output = Path(csv_dir).expanduser().resolve(), Path(output).expanduser().resolve()
    if output == _REPO_ROOT or _REPO_ROOT in output.parents:
        raise ValueError("출력 파일은 저장소 밖이어야 합니다.")
    script, counts = build_script(csv_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(script, encoding="utf-8")
    return counts


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    counts = export_cypher(args.csv_dir, args.output)
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
