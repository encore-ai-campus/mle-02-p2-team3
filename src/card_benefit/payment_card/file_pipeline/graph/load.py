"""Validate graph CSVs and optionally insert them into the fixed pf_ allowlist."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter
from pathlib import Path
import sys

from .export import ALLOWED_ENDPOINTS, CSV_COLUMNS

WRITE_TABLES = ("pf_load_runs", "pf_nodes", "pf_edges", "pf_evidence")
_INSERT_COLUMNS = {
    "pf_load_runs": CSV_COLUMNS["pf_load_runs"],
    "pf_nodes": CSV_COLUMNS["pf_nodes"],
    "pf_edges": CSV_COLUMNS["pf_edges"],
    # DB identity column is generated, so the CSV's seven columns are all inserted.
    "pf_evidence": CSV_COLUMNS["pf_evidence"],
}


class DuplicateRunError(ValueError):
    pass


class DatabaseOperationError(RuntimeError):
    def __init__(self, exception_class, sqlstate=None):
        self.exception_class = exception_class
        self.sqlstate = sqlstate
        message = f"Database operation failed ({exception_class})"
        if sqlstate:
            message += f" SQLSTATE={sqlstate}"
        super().__init__(message)


class DriverUnavailableError(RuntimeError):
    pass


class CSVValidationError(ValueError):
    def __init__(self, errors):
        self.errors = dict(errors)
        super().__init__(f"CSV validation failed: {self.errors}")


def _read(path, table):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != CSV_COLUMNS[table]:
            raise ValueError(f"Unexpected columns in {path.name}")
        return list(reader)


def validate_csvs(csv_dir):
    csv_dir = Path(csv_dir).expanduser().resolve()
    unexpected = sorted(p.name for p in csv_dir.glob("*.csv") if p.stem not in WRITE_TABLES)
    if unexpected:
        raise ValueError("CSV directory contains files outside the pf_ write allowlist")
    rows = {table: _read(csv_dir / f"{table}.csv", table) for table in WRITE_TABLES}
    errors = Counter()
    runs = rows["pf_load_runs"]
    if len(runs) != 1 or not runs[0].get("run_id"):
        errors["invalid_run_count"] += 1
    run_id = runs[0].get("run_id", "") if runs else ""
    if any(r.get("run_id") != run_id for table in ("pf_nodes", "pf_edges") for r in rows[table]):
        errors["run_id_mismatch"] += 1
    if runs:
        try:
            if int(runs[0]["node_count"]) != len(rows["pf_nodes"]) or int(runs[0]["edge_count"]) != len(rows["pf_edges"]):
                errors["run_count_mismatch"] += 1
        except (KeyError, TypeError, ValueError):
            errors["invalid_run_counts"] += 1
    nodes = rows["pf_nodes"]
    by_id = {}
    for row in nodes:
        if not row["id"] or row["id"] in by_id:
            errors["duplicate_node_id"] += 1
        by_id[row["id"]] = row
        if row["node_type"] not in {"Issuer", "Card", "Benefit", "Condition", "Limit", "Target"}:
            errors["invalid_node_type"] += 1
        try:
            if not isinstance(json.loads(row["props"]), dict):
                raise ValueError
        except (TypeError, ValueError):
            errors["invalid_props"] += 1
    edges = rows["pf_edges"]
    edge_ids = set()
    edge_keys = set()
    for row in edges:
        if not row["id"] or row["id"] in edge_ids:
            errors["duplicate_edge_id"] += 1
        edge_ids.add(row["id"])
        source, target = by_id.get(row["source_id"]), by_id.get(row["target_id"])
        if source is None or target is None:
            errors["missing_endpoint"] += 1
            continue
        expected = ALLOWED_ENDPOINTS.get(row["edge_type"])
        if not expected or (source["node_type"], target["node_type"]) != expected or (row["edge_type"] == "MUTUALLY_EXCLUSIVE" and row["source_id"] == row["target_id"]):
            errors["invalid_endpoint_types"] += 1
        edge_key = (row["source_id"], row["target_id"], row["edge_type"])
        if edge_key in edge_keys:
            errors["duplicate_edge_relation"] += 1
        edge_keys.add(edge_key)
    for row in rows["pf_evidence"]:
        if bool(row["node_id"]) == bool(row["edge_id"]):
            errors["invalid_evidence_target"] += 1
        elif row["node_id"] and row["node_id"] not in by_id or row["edge_id"] and row["edge_id"] not in edge_ids:
            errors["invalid_evidence_target"] += 1
        status = row["quote_status"]
        if status not in ("located", "ambiguous", "missing"):
            errors["invalid_quote_status"] += 1
            continue
        try:
            if not re.fullmatch(r"[0-9a-fA-F]{64}", row["doc_sha256"]):
                raise ValueError
            if status == "missing":
                if any(row[k] for k in ("page_no", "start_pos", "end_pos")):
                    raise ValueError
            elif int(row["page_no"]) < 1 or int(row["start_pos"]) < 1 or int(row["end_pos"]) < int(row["start_pos"]):
                raise ValueError
        except (ValueError, TypeError):
            errors["invalid_evidence_position"] += 1
    if errors:
        raise CSVValidationError(errors)
    return rows


def _connect(database_url):
    try:
        import psycopg
    except ImportError as exc:
        raise DriverUnavailableError("PostgreSQL driver psycopg is unavailable; install psycopg[binary,pool].") from exc
    return psycopg.connect(database_url)


def _table_for_sql(sql):
    match = re.match(r"INSERT INTO public\.(pf_[a-z_]+) ", sql)
    return match.group(1) if match else None


def _insert_sql(table):
    if table not in WRITE_TABLES:
        raise ValueError("table is not allowed")
    columns = _INSERT_COLUMNS[table]
    return f"INSERT INTO public.{table} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})"


def _jsonb(value):
    try:
        from psycopg.types.json import Jsonb
    except ImportError:
        return value
    return Jsonb(value)


def load_csvs(csv_dir, *, execute=False):
    rows = validate_csvs(csv_dir)
    counts = {table: len(rows[table]) for table in WRITE_TABLES}
    if not execute:
        return {"mode": "dry_run", "counts": counts}
    database_url = os.environ.get("PF_DATABASE_URL")
    if not database_url:
        raise RuntimeError("PF_DATABASE_URL is required for --execute")
    conn = None
    try:
        conn = _connect(database_url)
        with conn.cursor() as cursor:
            run_id = rows["pf_load_runs"][0]["run_id"]
            cursor.execute("SELECT 1 FROM public.pf_load_runs WHERE run_id = %s", (run_id,))
            if cursor.fetchone():
                raise DuplicateRunError("run_id already exists")
            for table in WRITE_TABLES:
                sql = _insert_sql(table)
                for row in rows[table]:
                    values = []
                    for column in _INSERT_COLUMNS[table]:
                        value = row[column]
                        if table == "pf_nodes" and column == "props":
                            value = _jsonb(json.loads(value))
                        elif table == "pf_evidence" and column in ("page_no", "start_pos", "end_pos"):
                            value = int(value) if value else None
                        elif table == "pf_load_runs" and column in ("node_count", "edge_count"):
                            value = int(value)
                        values.append(value)
                    cursor.execute(sql, tuple(values))
        conn.commit()
        return {"mode": "execute", "counts": counts}
    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        if isinstance(exc, (DuplicateRunError, DriverUnavailableError)):
            raise
        state = getattr(exc, "sqlstate", None)
        raise DatabaseOperationError(type(exc).__name__, str(state) if state else None) from None
    finally:
        if conn is not None:
            conn.close()


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = load_csvs(args.csv_dir, execute=args.execute)
    except Exception as exc:
        # Never serialize exception text or connection details.
        state = getattr(exc, "sqlstate", None)
        detail = {"error": getattr(exc, "exception_class", type(exc).__name__)}
        if state:
            detail["sqlstate"] = str(state)
        if isinstance(exc, DriverUnavailableError):
            detail["hint"] = "Install psycopg[binary,pool]."
        print(json.dumps(detail), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
