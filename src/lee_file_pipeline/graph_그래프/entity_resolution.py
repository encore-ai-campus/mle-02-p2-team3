"""Apply explicitly approved, within-card entity merges to graph CSVs.

This adapter uses only the Python standard library and never connects to a
database. Input and audit CSVs contain identifiers and properties, not source
document text.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

NODE_COLUMNS = ["id", "node_type", "props", "chunk_id", "run_id"]
EDGE_COLUMNS = ["id", "source_id", "target_id", "edge_type", "run_id"]
EVIDENCE_COLUMNS = ["node_id", "edge_id", "doc_sha256", "page_no", "start_pos", "end_pos", "quote_status"]
RUN_COLUMNS = ["run_id", "input_folder_name", "model_name", "started_at", "node_count", "edge_count"]
ALLOWED = {
    "HAS_CONDITION": ("Benefit", "Condition"), "HAS_LIMIT": ("Benefit", "Limit"),
    "APPLIES_TO": ("Benefit", "Target"), "EXCLUDES": ("Benefit", "Target"),
    "MUTUALLY_EXCLUSIVE": ("Benefit", "Benefit"), "OFFERS": ("Card", "Benefit"),
}
CORE = {"Benefit": ("method", "rate", "amount"), "Condition": ("kind", "min_amount"),
        "Limit": ("period", "amount", "unlimited", "shared"), "Target": ("kind",),
        "Card": ("issuer", "card_type")}
SPELLING = {"Benefit": "name", "Condition": "text", "Limit": "text", "Target": "text", "Card": "product_name"}
MAP_COLUMNS = ("group_id", "decision", "scope", "link_type", "card_scope_id", "canonical_node_id",
               "member_node_id", "reason_code", "evidence_ref", "reviewer", "reviewed_at")


def _read(path: Path, required: list[str]) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames) or reader.fieldnames != required:
                raise ValueError(f"{path}: expected exact columns {required}")
            rows = list(reader)
            if any(None in row or any(v is None for v in row.values()) for row in rows):
                raise ValueError(f"{path}: malformed row width")
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"cannot read CSV {path}: {exc}") from exc


def _write(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="raise")
        w.writeheader()
        w.writerows(rows)


def _props(row: dict[str, str]) -> dict:
    try:
        p = json.loads(row["props"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"node {row.get('id')}: invalid props JSON") from exc
    if not isinstance(p, dict):
        raise ValueError(f"node {row.get('id')}: props must be a JSON object")
    return p


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def transform(csv_dir: Path, mapping_csv: Path, output_dir: Path, audit_dir: Path, run_id: str) -> dict:
    csv_dir, mapping_csv, output_dir, audit_dir = (p.expanduser().resolve() for p in
                                                    (csv_dir, mapping_csv, output_dir, audit_dir))
    repo = Path(__file__).resolve().parents[3]
    if output_dir == audit_dir or output_dir.parent != audit_dir.parent:
        raise ValueError("output and audit directories must be distinct siblings")
    if any(p == repo or repo in p.parents for p in (output_dir, audit_dir)):
        raise ValueError("output and audit directories must be outside the repository")
    if output_dir == csv_dir or csv_dir in output_dir.parents or output_dir in csv_dir.parents:
        raise ValueError("input and output directories must not overlap")
    if audit_dir == csv_dir or csv_dir in audit_dir.parents or audit_dir in csv_dir.parents:
        raise ValueError("input and audit directories must not overlap")
    if not run_id.strip():
        raise ValueError("--m6-run-id must be non-empty")
    filenames = {"fp_nodes.csv": NODE_COLUMNS, "fp_edges.csv": EDGE_COLUMNS,
                 "fp_evidence.csv": EVIDENCE_COLUMNS, "fp_load_runs.csv": RUN_COLUMNS}
    data = {name: _read(csv_dir / name, columns) for name, columns in filenames.items()}
    nodes, edges, evidence, runs = (data[n] for n in ("fp_nodes.csv", "fp_edges.csv", "fp_evidence.csv", "fp_load_runs.csv"))
    if len(runs) != 1 or not runs[0]["run_id"]:
        raise ValueError("input fp_load_runs.csv must contain exactly one run")
    source_run = runs[0]["run_id"]
    try:
        if int(runs[0]["node_count"]) != len(nodes) or int(runs[0]["edge_count"]) != len(edges):
            raise ValueError("fp_load_runs counts do not match input rows")
    except ValueError as exc:
        if str(exc) == "fp_load_runs counts do not match input rows": raise
        raise ValueError("fp_load_runs node_count/edge_count must be integers") from exc
    if any(n["run_id"] != source_run for n in nodes) or any(e["run_id"] != source_run for e in edges):
        raise ValueError("input node/edge run_id values must match fp_load_runs.csv")
    by_id = {}
    props = {}
    for n in nodes:
        if not n["id"] or n["id"] in by_id or n["node_type"] not in {"Card", "Benefit", "Condition", "Limit", "Target"}:
            raise ValueError("node IDs must be non-empty and unique; node_type required")
        by_id[n["id"]] = n
        props[n["id"]] = _props(n)
    edge_ids = set()
    for e in edges:
        if not e["id"] or e["id"] in edge_ids:
            raise ValueError("edge IDs must be non-empty and unique")
        edge_ids.add(e["id"])
        expected = ALLOWED.get(e["edge_type"])
        if not expected or e["source_id"] not in by_id or e["target_id"] not in by_id:
            raise ValueError(f"edge {e['id']}: unknown type or dangling endpoint")
        if (by_id[e['source_id']]['node_type'], by_id[e['target_id']]['node_type']) != expected:
            raise ValueError(f"edge {e['id']}: invalid endpoint types")
        if e["source_id"] == e["target_id"]:
            raise ValueError(f"edge {e['id']}: self-loop")

    # Compute the set of cards reaching each node through the directed graph.
    outgoing = {nid: [] for nid in by_id}
    for e in edges:
        outgoing[e["source_id"]].append(e["target_id"])
    cards = {nid: set() for nid in by_id}
    for nid, n in by_id.items():
        if n["node_type"] == "Card":
            cards[nid].add(nid)
    changed = True
    while changed:
        changed = False
        for e in edges:
            new = cards[e["source_id"]] | cards[e["target_id"]] if e["edge_type"] != "OFFERS" else cards[e["source_id"]]
            # OFFERS carries Card scope forward; the remaining domain edges carry it forward.
            if e["edge_type"] == "OFFERS":
                new = cards[e["source_id"]]
            if not new.issubset(cards[e["target_id"]]):
                cards[e["target_id"]].update(new); changed = True
    mappings = _read(mapping_csv, list(MAP_COLUMNS)) if mapping_csv.exists() else []
    groups: dict[str, list[dict[str, str]]] = {}
    member_owner: dict[str, str] = {}
    remap = {nid: nid for nid in by_id}
    for r in mappings:
        decision = r["decision"]
        if decision not in {"merge", "keep", "defer"}:
            raise ValueError(f"invalid mapping decision {decision!r}")
        if (not r["group_id"] or r["scope"] not in {"within_card", "across_cards"}
                or not r["card_scope_id"] or not r["canonical_node_id"] or not r["member_node_id"]
                or r["canonical_node_id"] not in by_id or r["member_node_id"] not in by_id):
            raise ValueError("mapping rows require group/scope/card scope and existing canonical/member IDs")
        expected_link = "SAME_AS_STRONG" if r["scope"] == "within_card" else "SIMILAR"
        if r["link_type"] != expected_link:
            raise ValueError("within_card requires SAME_AS_STRONG; across_cards requires SIMILAR")
        if decision == "merge":
            if r["scope"] != "within_card":
                raise ValueError("only within_card mappings may merge")
            if not all(r[k].strip() for k in ("reason_code", "evidence_ref", "reviewer", "reviewed_at")):
                raise ValueError("merge rows require reason_code, evidence_ref, reviewer, and reviewed_at")
            groups.setdefault(r["group_id"], []).append(r)
    for gid, rows in groups.items():
        canonicals = {r["canonical_node_id"] for r in rows}
        scopes = {r["card_scope_id"] for r in rows}
        members = [r["member_node_id"] for r in rows]
        if len(canonicals) != 1 or len(scopes) != 1 or len(set(members)) != len(members):
            raise ValueError(f"group {gid}: inconsistent canonical/card scope or repeated member")
        canonical = next(iter(canonicals))
        card_scope_id = next(iter(scopes))
        if canonical not in members or canonical not in by_id:
            raise ValueError(f"group {gid}: canonical must be an existing member")
        for member in members:
            if member not in by_id:
                raise ValueError(f"group {gid}: unknown member {member}")
            if member in member_owner:
                raise ValueError(f"member {member} occurs in multiple merge groups")
            member_owner[member] = gid
            if by_id[member]["node_type"] != by_id[canonical]["node_type"]:
                raise ValueError(f"group {gid}: node types differ")
            if not cards[member] or cards[member] != cards[canonical]:
                raise ValueError(f"group {gid}: derived card membership differs or is empty")
            if card_scope_id not in cards[member]:
                raise ValueError(f"group {gid}: card_scope_id does not match derived card membership")
            for key in set(CORE.get(by_id[member]["node_type"], ())) | set(CORE.get(by_id[canonical]["node_type"], ())):
                if props[member].get(key) != props[canonical].get(key):
                    raise ValueError(f"group {gid}: conflicting core property {key}")
            remap[member] = canonical
    # Resolve chains defensively and reject cycles, even though group validation usually disallows them.
    for nid in remap:
        seen = set(); cur = nid
        while remap[cur] != cur:
            if cur in seen: raise ValueError("mapping cycle")
            seen.add(cur); cur = remap[cur]
        remap[nid] = cur
    out_nodes = []
    alias_rows = []
    for nid, n in by_id.items():
        c = remap[nid]
        if c != nid:
            spelling_key = SPELLING.get(n["node_type"])
            if spelling_key and props[nid].get(spelling_key) not in (None, "", props[c].get(spelling_key)):
                alias_rows.append({"canonical_node_id": c, "alias_node_id": nid, "property": spelling_key,
                                   "alias_value": str(props[nid][spelling_key]), "group_id": member_owner[nid]})
            continue
        out_nodes.append(dict(n, run_id=run_id))
    survivor = {}
    collapsed = {}
    out_edges = []
    key_to_edge = {}
    for e in edges:
        source, target = remap[e["source_id"]], remap[e["target_id"]]
        if source == target:
            raise ValueError(f"edge {e['id']}: merge would create self-loop")
        key = (source, target, e["edge_type"])
        prior = key_to_edge.get(key)
        if prior:
            collapsed[e["id"]] = prior
            survivor[e["id"]] = prior
        else:
            key_to_edge[key] = e["id"]
            survivor[e["id"]] = e["id"]
            out_edges.append(dict(e, source_id=source, target_id=target, run_id=run_id))
    out_evidence = []
    for e in evidence:
        has_node, has_edge = bool(e["node_id"]), bool(e["edge_id"])
        if has_node == has_edge:
            raise ValueError("evidence must target exactly one node_id or edge_id")
        if has_node:
            if e["node_id"] not in by_id: raise ValueError("evidence has dangling node target")
            row = dict(e, node_id=remap[e["node_id"]])
        else:
            if e["edge_id"] not in survivor: raise ValueError("evidence has dangling edge target")
            row = dict(e, edge_id=survivor[e["edge_id"]])
        status = row["quote_status"]
        if status not in {"located", "ambiguous", "missing"}:
            raise ValueError("invalid quote_status")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", row["doc_sha256"]): raise ValueError("invalid evidence doc_sha256")
        vals = (row["page_no"], row["start_pos"], row["end_pos"])
        if status == "located":
            try:
                page, start, end = map(int, vals)
                if page < 1 or start < 1 or end < start: raise ValueError
            except (ValueError, TypeError): raise ValueError("invalid located quote positions")
        elif any(v != "" for v in vals):
            raise ValueError("unlocated evidence must have blank positions")
        out_evidence.append(row)
    out_run = dict(runs[0], run_id=run_id, node_count=str(len(out_nodes)), edge_count=str(len(out_edges)))
    node_audit = [{"node_id": n, "canonical_node_id": c, "changed": str(n != c).lower()} for n, c in sorted(remap.items())]
    edge_audit = [{"edge_id": e, "survivor_edge_id": survivor[e], "collapsed": str(e in collapsed).lower()} for e in sorted(survivor)]
    summary = [{"input_nodes": str(len(nodes)), "output_nodes": str(len(out_nodes)), "input_edges": str(len(edges)),
                "output_edges": str(len(out_edges)), "collapsed_edges": str(len(collapsed)), "input_evidence": str(len(evidence)),
                "output_evidence": str(len(out_evidence)),
                "preserved_mapping_rows": str(sum(r["decision"] != "merge" for r in mappings)),
                "keep_rows": str(sum(r["decision"] == "keep" for r in mappings)),
                "defer_rows": str(sum(r["decision"] == "defer" for r in mappings)),
                "mapping_sha256": hashlib.sha256(mapping_csv.read_bytes()).hexdigest() if mapping_csv.exists() else ""}]
    mapping_audit = [dict(r, applied=str(r["decision"] == "merge").lower()) for r in mappings]
    for directory in (output_dir, audit_dir):
        if directory.exists() and any(directory.iterdir()): raise FileExistsError(f"directory is not empty: {directory}")
    output_dir.parent.mkdir(parents=True, exist_ok=True); audit_dir.parent.mkdir(parents=True, exist_ok=True)
    # Stage both trees first; publish only after every validation and write succeeds.
    with tempfile.TemporaryDirectory(prefix="er-stage-", dir=output_dir.parent) as td:
        stage = Path(td); data_stage = stage / "data"; audit_stage = stage / "audit"
        data_stage.mkdir(); audit_stage.mkdir()
        _write(data_stage / "fp_load_runs.csv", RUN_COLUMNS, [out_run])
        _write(data_stage / "fp_nodes.csv", NODE_COLUMNS, out_nodes)
        _write(data_stage / "fp_edges.csv", EDGE_COLUMNS, out_edges)
        _write(data_stage / "fp_evidence.csv", EVIDENCE_COLUMNS, out_evidence)
        _write(audit_stage / "node_mapping.csv", ["node_id", "canonical_node_id", "changed"], node_audit)
        _write(audit_stage / "edge_mapping.csv", ["edge_id", "survivor_edge_id", "collapsed"], edge_audit)
        _write(audit_stage / "aliases.csv", ["canonical_node_id", "alias_node_id", "property", "alias_value", "group_id"], alias_rows)
        _write(audit_stage / "summary.csv", list(summary[0]), summary)
        _write(audit_stage / "mapping_decisions.csv", [*MAP_COLUMNS, "applied"], mapping_audit)
        manifest = []
        for f in sorted(data_stage.iterdir()):
            payload = f.read_bytes()
            with f.open(encoding="utf-8", newline="") as csv_file:
                row_count = max(0, sum(1 for _ in csv.reader(csv_file)) - 1)
            manifest.append({"file": f.name, "row_count": str(row_count),
                             "sha256": hashlib.sha256(payload).hexdigest()})
        _write(audit_stage / "output_manifest.csv", ["file", "row_count", "sha256"], manifest)
        if output_dir.exists() and any(output_dir.iterdir()) or audit_dir.exists() and any(audit_dir.iterdir()):
            raise FileExistsError("output/audit directory became non-empty")
        output_dir.mkdir(parents=True, exist_ok=True); audit_dir.mkdir(parents=True, exist_ok=True)
        for src in data_stage.iterdir(): os.replace(src, output_dir / src.name)
        for src in audit_stage.iterdir(): os.replace(src, audit_dir / src.name)
    return summary[0]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv-dir", required=True, type=Path, help="directory containing the four exporter CSVs")
    p.add_argument("--mapping-csv", required=True, type=Path, help="human-approved CSV; only explicit merge rows rewrite IDs")
    p.add_argument("--output-dir", required=True, type=Path, help="fresh directory for exactly four Neo4j import CSVs")
    p.add_argument("--audit-dir", type=Path, help="fresh sibling directory (default: <output-dir>_audit)")
    p.add_argument("--m6-run-id", required=True, help="new import run ID written to load-runs, node, and edge rows")
    a = p.parse_args(argv)
    audit = a.audit_dir or a.output_dir.with_name(a.output_dir.name + "_audit")
    try:
        result = transform(a.csv_dir, a.mapping_csv, a.output_dir, audit, a.m6_run_id)
    except (ValueError, OSError) as exc:
        p.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
