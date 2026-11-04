import csv
import json

from payment_card.file_pipeline.graph import load


def _csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers); w.writeheader(); w.writerows(rows)


def _files(tmp_path):
    _csv(tmp_path / "pf_load_runs.csv", ["run_id", "input_folder_name", "model_name", "started_at", "node_count", "edge_count"],
         [{"run_id": "r1", "input_folder_name": "in", "model_name": "m", "started_at": "2026-01-01T00:00:00+00:00", "node_count": 2, "edge_count": 1}])
    _csv(tmp_path / "pf_nodes.csv", ["id", "node_type", "props", "chunk_id", "run_id"],
         [{"id": "a", "node_type": "Benefit", "props": json.dumps({}), "chunk_id": "c", "run_id": "r1"}, {"id": "b", "node_type": "Condition", "props": "{}", "chunk_id": "c", "run_id": "r1"}])
    _csv(tmp_path / "pf_edges.csv", ["id", "source_id", "target_id", "edge_type", "run_id"],
         [{"id": "e", "source_id": "a", "target_id": "b", "edge_type": "HAS_CONDITION", "run_id": "r1"}])
    _csv(tmp_path / "pf_evidence.csv", ["node_id", "edge_id", "doc_sha256", "page_no", "start_pos", "end_pos", "quote_status"], [])


def test_dry_run_never_connects(tmp_path, monkeypatch, capsys):
    _files(tmp_path)
    monkeypatch.setattr(load, "_connect", lambda _: (_ for _ in ()).throw(AssertionError("connected")))
    assert load.main(["--csv-dir", str(tmp_path)]) == 0
    assert capsys.readouterr().out == '{"counts": {"pf_edges": 1, "pf_evidence": 0, "pf_load_runs": 1, "pf_nodes": 2}, "mode": "dry_run"}\n'


class FakeCursor:
    def __init__(self, duplicate=False): self.calls=[]; self.batch_calls=[]; self.duplicate=duplicate; self.counts=[]
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
    def executemany(self, sql, rows): self.batch_calls.append((sql, list(rows)))
    def fetchone(self):
        if self.counts: return (self.counts.pop(0),)
        if self.calls and self.calls[-1][0].startswith("SELECT COUNT"): return (0,)
        return (1,) if self.duplicate else None
    def fetchall(self): return [(n,) for n in self.counts]
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def close(self): pass


class FakeConn:
    def __init__(self, duplicate=False, fail=False): self.cur=FakeCursor(duplicate); self.events=[]; self.fail=fail
    def cursor(self): return self.cur
    def commit(self): self.events.append("commit")
    def rollback(self): self.events.append("rollback")
    def close(self): self.events.append("close")


def test_execute_inserts_in_allowlisted_order_and_duplicate_rolls_back(tmp_path, monkeypatch):
    _files(tmp_path)
    conn=FakeConn(); monkeypatch.setattr(load, "_connect", lambda url: conn); monkeypatch.setenv("PF_DATABASE_URL", "secret")
    load.load_csvs(tmp_path, execute=True)
    tables=[load._table_for_sql(sql) for sql, _ in conn.cur.batch_calls]
    assert tables == ["pf_load_runs", "pf_nodes", "pf_edges"]
    assert conn.events == ["commit", "close"]
    dup=FakeConn(duplicate=True); monkeypatch.setattr(load, "_connect", lambda url: dup)
    try: load.load_csvs(tmp_path, execute=True)
    except load.DuplicateRunError: pass
    else: assert False, "duplicate must reject"
    assert dup.events == ["rollback", "close"]


def test_execute_failure_rolls_back_and_never_prints_database_url(tmp_path, monkeypatch, capsys):
    _files(tmp_path)
    class FailingCursor(FakeCursor):
        def executemany(self, sql, rows):
            super().executemany(sql, rows)
            if sql.startswith("INSERT INTO public.pf_nodes"):
                error = RuntimeError("secret connection contents")
                error.sqlstate = "XX001"
                raise error
    class FailingConn(FakeConn):
        def __init__(self): super().__init__(); self.cur=FailingCursor()
    conn=FailingConn(); monkeypatch.setattr(load, "_connect", lambda url: conn); monkeypatch.setenv("PF_DATABASE_URL", "secret-dsn")
    assert load.main(["--csv-dir", str(tmp_path), "--execute"]) == 1
    output=capsys.readouterr().err
    assert "secret-dsn" not in output and "secret connection contents" not in output
    assert "RuntimeError" in output and "XX001" in output
    assert conn.events == ["rollback", "close"]


def test_execute_batches_rows_by_1000_and_preserves_table_order(tmp_path, monkeypatch):
    _files(tmp_path)
    rows = []
    for i in range(2500):
        rows.append({"id": f"n{i}", "node_type": "Benefit", "props": "{}", "chunk_id": "c", "run_id": "r1"})
    _csv(tmp_path / "pf_nodes.csv", ["id", "node_type", "props", "chunk_id", "run_id"], rows)
    _csv(tmp_path / "pf_load_runs.csv", ["run_id", "input_folder_name", "model_name", "started_at", "node_count", "edge_count"],
         [{"run_id": "r1", "input_folder_name": "in", "model_name": "m", "started_at": "2026-01-01T00:00:00+00:00", "node_count": 2500, "edge_count": 0}])
    _csv(tmp_path / "pf_edges.csv", ["id", "source_id", "target_id", "edge_type", "run_id"], [])
    conn = FakeConn(); monkeypatch.setattr(load, "_connect", lambda _: conn); monkeypatch.setenv("PF_DATABASE_URL", "unused")
    result = load.load_csvs(tmp_path, execute=True)
    assert result == {"mode": "execute", "counts": {"pf_load_runs": 1, "pf_nodes": 2500, "pf_edges": 0, "pf_evidence": 0}}
    assert [(load._table_for_sql(sql), len(batch)) for sql, batch in conn.cur.batch_calls] == [
        ("pf_load_runs", 1), ("pf_nodes", 1000), ("pf_nodes", 1000), ("pf_nodes", 500)
    ]
    assert conn.events == ["commit", "close"]


def test_delete_run_dry_run_only_counts(tmp_path, monkeypatch):
    conn = FakeConn(); conn.cur.counts = [2, 3, 4, 5]
    monkeypatch.setattr(load, "_connect", lambda _: conn); monkeypatch.setenv("PF_DATABASE_URL", "unused")
    assert load.delete_run("r1") == {"mode": "dry_run", "counts": {"pf_evidence": 2, "pf_edges": 3, "pf_nodes": 4, "pf_load_runs": 5}}
    assert all(not sql.startswith("DELETE") for sql, _ in conn.cur.calls)
    assert conn.events == ["close"]


def test_delete_run_execute_order_parameters_and_unknown_run(tmp_path, monkeypatch):
    conn = FakeConn(); monkeypatch.setattr(load, "_connect", lambda _: conn); monkeypatch.setenv("PF_DATABASE_URL", "unused")
    assert load.delete_run("r1", execute=True)["mode"] == "execute"
    deletes = [(sql, params) for sql, params in conn.cur.calls if sql.startswith("DELETE")]
    assert [sql.split(" public.")[1].split()[0] for sql, _ in deletes] == ["pf_evidence", "pf_edges", "pf_nodes", "pf_load_runs"]
    assert all(params == ("r1", "r1") if sql.startswith("DELETE FROM public.pf_evidence") else params == ("r1",) for sql, params in deletes)
    assert conn.events == ["commit", "close"]
    unknown = FakeConn(); monkeypatch.setattr(load, "_connect", lambda _: unknown)
    assert load.delete_run("absent")["counts"] == {"pf_evidence": 0, "pf_edges": 0, "pf_nodes": 0, "pf_load_runs": 0}


def test_unallowlisted_csv_is_rejected(tmp_path):
    _files(tmp_path)
    (tmp_path / "public_nodes.csv").write_text("id\n", encoding="utf-8")
    try:
        load.validate_csvs(tmp_path)
    except ValueError as exc:
        assert "allowlist" in str(exc)
    else:
        assert False, "unallowlisted table file must be rejected"
