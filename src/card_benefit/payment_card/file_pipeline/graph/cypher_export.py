"""Export graph CSV files as an idempotent, APOC-free Neo4j Browser script."""
from __future__ import annotations

import argparse
import csv
import json
import hashlib
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_LABELS = ("Issuer", "Card", "Benefit", "Condition", "Limit", "Target")
_RELATION_TYPES = ("HAS_CONDITION", "HAS_LIMIT", "APPLIES_TO", "EXCLUDES", "MUTUALLY_EXCLUSIVE", "OFFERS")
_RELATION_LABELS = {
    "OFFERS": ("Card", "Benefit"), "HAS_CONDITION": ("Benefit", "Condition"),
    "HAS_LIMIT": ("Benefit", "Limit"), "APPLIES_TO": ("Benefit", "Target"),
    "EXCLUDES": ("Benefit", "Target"), "MUTUALLY_EXCLUSIVE": ("Benefit", "Benefit"),
}
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
        raise ValueError("fp_nodes.props는 JSON 객체여야 합니다.")
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


def _data(csv_dir: Path):
    nodes = _read_rows(csv_dir / "fp_nodes.csv")
    edges = _read_rows(csv_dir / "fp_edges.csv")
    evidence = _read_rows(csv_dir / "fp_evidence.csv")
    for row in nodes:
        row["parsed_props"] = _node_props(row.get("props", "{}"))
    return nodes, edges, evidence


def _name(props):
    for key in ("product_name", "productName", "name", "card_name", "title"):
        if props.get(key):
            return str(props[key])
    return ""


def _caption(label, node_id, props):
    if label == "Card":
        return str(props.get("product_name") or node_id)
    if label == "Issuer":
        return str(props.get("name") or props.get("issuer_name") or props.get("issuer") or node_id)
    if label == "Benefit":
        return str(props.get("name") or node_id)
    if label in ("Condition", "Limit", "Target"):
        return str(props.get("text") or f"{label.lower()}-{node_id[-6:]}")[:30]
    return str(node_id)


def _evidence_id(row):
    parts = [row.get(key, "") or "" for key in
             ("node_id", "edge_id", "doc_sha256", "page_no", "start_pos", "end_pos", "quote_status")]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]
    return f"evidence:{digest}"


def list_cards(csv_dir: Path, limit: int) -> list[dict]:
    nodes, edges, evidence = _data(csv_dir)
    by_id = {n["id"]: n for n in nodes}
    evidence_nodes = {e.get("node_id") for e in evidence if e.get("node_id")}
    evidence_edges = {e.get("edge_id") for e in evidence if e.get("edge_id")}
    rows = []
    for card in nodes:
        if card["node_type"] != "Card":
            continue
        offers = [e for e in edges if e["edge_type"] == "OFFERS" and e["source_id"] == card["id"] and e["target_id"] in by_id and by_id[e["target_id"]]["node_type"] == "Benefit"]
        benefits = {e["target_id"] for e in offers}
        details = {"Condition": set(), "Limit": set(), "Target": set()}
        for edge in edges:
            if edge["source_id"] in benefits and edge["edge_type"] in ("HAS_CONDITION", "HAS_LIMIT", "APPLIES_TO", "EXCLUDES") and edge["target_id"] in by_id:
                typ = by_id[edge["target_id"]]["node_type"]
                if typ == "Condition": details["Condition"].add(edge["target_id"])
                elif typ == "Limit": details["Limit"].add(edge["target_id"])
                elif typ == "Target": details["Target"].add(edge["target_id"])
        linked_edge_ids = {e["id"] for e in edges if e["source_id"] == card["id"] or e["source_id"] in benefits}
        rows.append({"card_id": card["id"], "product_name": _name(card["parsed_props"]), "benefits": len(benefits),
                     "conditions": len(details["Condition"]), "limits": len(details["Limit"]), "targets": len(details["Target"]),
                     "evidence": sum(1 for e in evidence if (e.get("node_id") in {card["id"]} | benefits | details["Condition"] | details["Limit"] | details["Target"]) or e.get("edge_id") in linked_edge_ids)})
    rows.sort(key=lambda r: (-r["benefits"], r["card_id"]))
    return rows[:limit]


def _sample_rows(nodes, edges, evidence, card_ids, max_benefits):
    by_id = {n["id"]: n for n in nodes}
    kept_benefits, chosen_cards, cut = set(), set(), 0
    selected_edges = set()
    for card_id in card_ids:
        card = by_id.get(card_id)
        if not card or card["node_type"] != "Card":
            raise ValueError(f"카드 id를 찾을 수 없습니다: {card_id}")
        chosen_cards.add(card_id)
        offers = [e for e in edges if e["edge_type"] == "OFFERS" and e["source_id"] == card_id and by_id.get(e["target_id"], {}).get("node_type") == "Benefit"]
        def score(edge):
            bid = edge["target_id"]
            return (sum(1 for x in edges if x["source_id"] == bid and x["edge_type"] in ("HAS_CONDITION", "HAS_LIMIT", "APPLIES_TO", "EXCLUDES")), bid)
        offers.sort(key=lambda e: (-score(e)[0], score(e)[1]))
        cut += max(0, len(offers) - max_benefits)
        for edge in offers[:max_benefits]:
            kept_benefits.add(edge["target_id"])
            selected_edges.add(edge["id"])
    related_edges = []
    for edge in edges:
        source, target, typ = edge["source_id"], edge["target_id"], edge["edge_type"]
        keep = edge["id"] in selected_edges
        if typ in ("HAS_CONDITION", "HAS_LIMIT", "APPLIES_TO", "EXCLUDES") and source in kept_benefits:
            keep = True
        if typ == "MUTUALLY_EXCLUSIVE" and source in kept_benefits and target in kept_benefits:
            keep = True
        # Edges between selected benefits and any other card are intentionally excluded.
        if typ == "OFFERS" and source not in chosen_cards:
            keep = False
        if keep:
            related_edges.append(edge)
    node_ids = chosen_cards | kept_benefits
    node_ids.update(e["target_id"] for e in related_edges if e["edge_type"] != "OFFERS")
    selected_nodes = [n for n in nodes if n["id"] in node_ids]
    edge_ids = {e["id"] for e in related_edges}
    selected_evidence = [e for e in evidence if (e.get("node_id") and e["node_id"] in node_ids) or (e.get("edge_id") and e["edge_id"] in edge_ids)]
    return selected_nodes, related_edges, selected_evidence, cut


def _build(nodes, edges, evidence, header=None):
    lines = [header or "// Neo4j Browser용 CSV 적재 스크립트. 재실행 가능한 MERGE를 사용합니다."]
    for label in _LABELS:
        lines.append(f"CREATE CONSTRAINT fp_{label.lower()}_id_unique IF NOT EXISTS FOR (n:Fp{label}) REQUIRE n.id IS UNIQUE;")
    lines.append("CREATE CONSTRAINT fp_evidence_id_unique IF NOT EXISTS FOR (e:FpEvidence) REQUIRE e.id IS UNIQUE;")

    for label in _LABELS:
        label_rows = []
        for row in nodes:
            if _validated_type(row["node_type"], _LABELS, "node_type") != label:
                continue
            props = row.get("parsed_props", _node_props(row.get("props", "{}")))
            props.update({"id": row["id"], "run_id": row.get("run_id", ""), "chunk_id": row.get("chunk_id", "")})
            props["name"] = _caption(label, row["id"], props)
            label_rows.append(props)
        lines.extend(_unwind(label_rows, f"MERGE (n:Fp{label} {{id: row.id}})\nSET n += row;"))

    for rel_type in _RELATION_TYPES:
        rel_rows = [row for row in edges if _validated_type(row["edge_type"], _RELATION_TYPES, "edge_type") == rel_type]
        source_label, target_label = _RELATION_LABELS[rel_type]
        clause = (f"MATCH (source:Fp{source_label} {{id: row.source_id}}), (target:Fp{target_label} {{id: row.target_id}})\n"
                  f"MERGE (source)-[r:FP_{rel_type} {{id: row.id}}]->(target)\nSET r.run_id = row.run_id;")
        lines.extend(_unwind(rel_rows, clause))

    evidence_rows = []
    unique_evidence = {}
    for row in evidence:
        evidence_id = _evidence_id(row)
        values = {"id": evidence_id, "evidence_id": evidence_id, "doc_sha256": row["doc_sha256"],
                  "page_no": int(row["page_no"]) if row.get("page_no") else None,
                  "start_pos": int(row["start_pos"]) if row.get("start_pos") else None,
                  "end_pos": int(row["end_pos"]) if row.get("end_pos") else None,
                  "quote_status": row["quote_status"]}
        values["name"] = (f"{row['quote_status']} p.{row['page_no']}" if row.get("page_no") else str(row["quote_status"]))
        if row.get("edge_id"):
            values["edge_id"] = row["edge_id"]
        if row.get("node_id"):
            values["node_id"] = row["node_id"]
        unique_evidence.setdefault(evidence_id, values)
    evidence_rows = list(unique_evidence.values())
    lines.append("// 관계 자체에는 Evidence 노드를 연결할 수 없어 edge 근거에는 edge_id를 저장합니다.")
    evidence_clause = "MERGE (e:FpEvidence {id: row.id})\nSET e += row;"
    # 라벨+id MERGE 후 SET n += row는 같은 식별 데이터의 재적재 때만 기존 Fp 노드를 덮습니다.
    lines.extend(_unwind(evidence_rows, evidence_clause))
    for label in _LABELS:
        linked = [row for row in evidence_rows if row.get("node_id") and any(n["id"] == row["node_id"] and n["node_type"] == label for n in nodes)]
        if linked:
            clause = f"MATCH (n:Fp{label} {{id: row.node_id}})\nMATCH (e:FpEvidence {{id: row.id}})\nMERGE (n)-[:FP_HAS_EVIDENCE]->(e);"
            lines.extend(_unwind(linked, clause))
    counts = {"nodes": len(nodes), "edges": len(edges), "evidence": len(evidence_rows)}
    return "\n\n".join(lines) + "\n", counts


def build_script(csv_dir: Path) -> tuple[str, dict[str, int]]:
    return _build(*_data(csv_dir))


def export_cypher(csv_dir: str | Path, output: str | Path, card_ids=None, max_benefits=15) -> dict[str, int]:
    csv_dir, output = Path(csv_dir).expanduser().resolve(), Path(output).expanduser().resolve()
    if output == _REPO_ROOT or _REPO_ROOT in output.parents:
        raise ValueError("출력 파일은 저장소 밖이어야 합니다.")
    nodes, edges, evidence = _data(csv_dir)
    if card_ids:
        nodes, edges, evidence, cut = _sample_rows(nodes, edges, evidence, card_ids, max_benefits)
        header = ("// 샘플 스크립트: 선택 카드 " + ", ".join(card_ids) +
                  f"; 노드 {len(nodes)}, 엣지 {len(edges)}, 근거 {len(evidence)}, 잘린 혜택 {cut}")
        script, counts = _build(nodes, edges, evidence, header)
        counts["cut_benefits"] = cut
    else:
        script, counts = _build(nodes, edges, evidence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(script, encoding="utf-8")
    return counts


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--output")
    parser.add_argument("--list-cards", type=int)
    parser.add_argument("--card-id", action="append", default=[])
    parser.add_argument("--max-benefits", type=int, default=15)
    args = parser.parse_args(argv)
    if args.list_cards is not None:
        print("card_id\tproduct_name\tbenefits\tconditions\tlimits\ttargets\tevidence")
        for row in list_cards(Path(args.csv_dir).expanduser(), args.list_cards):
            print("\t".join(str(row[k]) for k in ("card_id", "product_name", "benefits", "conditions", "limits", "targets", "evidence")))
        return
    if not args.output:
        parser.error("--output is required unless --list-cards is used")
    counts = export_cypher(args.csv_dir, args.output, args.card_id or None, args.max_benefits)
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
