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
    assert '"pf_nodes": 2' in capsys.readouterr().out


class FakeCursor:
    def __init__(self, duplicate=False): self.calls=[]; self.duplicate=duplicate
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
    def fetchone(self): return (1,) if self.duplicate else None
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
    tables=[load._table_for_sql(sql) for sql, _ in conn.cur.calls if sql.startswith("INSERT")]
    assert tables == ["pf_load_runs", "pf_nodes", "pf_nodes", "pf_edges"]
    assert conn.events == ["commit", "close"]
    dup=FakeConn(duplicate=True); monkeypatch.setattr(load, "_connect", lambda url: dup)
    try: load.load_csvs(tmp_path, execute=True)
    except load.DuplicateRunError: pass
    else: assert False, "duplicate must reject"
    assert dup.events == ["rollback", "close"]


def test_execute_failure_rolls_back_and_never_prints_database_url(tmp_path, monkeypatch, capsys):
    _files(tmp_path)
    class FailingCursor(FakeCursor):
        def execute(self, sql, params=None):
            super().execute(sql, params)
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


def test_unallowlisted_csv_is_rejected(tmp_path):
    _files(tmp_path)
    (tmp_path / "public_nodes.csv").write_text("id\n", encoding="utf-8")
    try:
        load.validate_csvs(tmp_path)
    except ValueError as exc:
        assert "allowlist" in str(exc)
    else:
        assert False, "unallowlisted table file must be rejected"
