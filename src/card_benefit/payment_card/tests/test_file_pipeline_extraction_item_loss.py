from __future__ import annotations

import json

from payment_card.file_pipeline.extraction.item_loss_report import build_report


def _row(chunk_id, benefits=None, conditions=None, limits=None, targets=None, relations=None):
    return {"chunk_id": chunk_id, "extraction": {
        "benefits": benefits or [], "conditions": conditions or [], "limits": limits or [],
        "targets": targets or [], "relations": relations or [],
    }}


def _benefit(name="a", method="DISCOUNT", ident="b"):
    return {"id": ident, "name": name, "method": method, "evidence": [{"text": "SENSITIVE_QUOTE"}]}


def _write_run(directory, rows):
    directory.mkdir()
    for row in rows:
        (directory / f"{row['chunk_id']}.result.json").write_text(json.dumps(row), encoding="utf-8")


def test_item_loss_report_counts_persistent_loss_unstable_types_additions_and_hides_text(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()
    (chunks / "doc.chunks.json").write_text(json.dumps({"chunks": [
        {"chunk_id": "c1", "text": "표 5% 10원\n짧은 값"},
    ]}), encoding="utf-8")
    common = _benefit("SENSITIVE_NAME", "CASHBACK", "same")
    unstable = {"id": "unstable", "name": "rare", "method": "POINT"}
    condition = {"id": "c", "text": "조건길이열한글자", "kind": "SPEND_REQ"}
    limit = {"id": "l", "text": "한도", "period": "MONTH", "shared": True, "unlimited": False}
    target = {"id": "t", "text": "대상 이름", "kind": "MERCHANT"}
    rel = {"source": "same", "target": "c", "type": "HAS_CONDITION"}
    base_dirs = []
    for i in range(4):
        path = tmp_path / f"base{i}"
        _write_run(path, [_row("c1", [common] + ([unstable] if i == 0 else []), [condition], [limit], [target], [rel])])
        base_dirs.append(path)
    compare = tmp_path / "compare"
    added = _benefit("new-item", "DISCOUNT", "new")
    _write_run(compare, [_row("c1", [added])])

    report = build_report(base_dirs, [compare], chunks)
    lost = report["disappeared_candidates"]
    assert report["base_threshold_at_least"] == 3
    assert lost["total"] == 5
    assert lost["by_section"] == {"benefits": 1, "conditions": 1, "limits": 1, "targets": 1, "relations": 1}
    assert lost["by_type"]["benefits"] == {"CASHBACK": 1}
    assert lost["by_type"]["conditions"] == {"SPEND_REQ": 1}
    assert lost["by_type"]["limits"] == {"MONTH|shared|limited": 1}
    assert lost["by_type"]["targets"] == {"MERCHANT": 1}
    assert lost["by_type"]["relations"] == {"HAS_CONDITION": 1}
    assert report["base_once_only_unstable"]["total"] == 1
    assert report["base_once_only_unstable"]["by_type"]["benefits"] == {"POINT": 1}
    assert report["compare_only_added"]["total"] == 1
    assert report["compare_only_added"]["by_type"]["benefits"] == {"DISCOUNT": 1}
    assert sum(lost["by_length"].values()) == lost["total"]
    assert sum(lost["by_table_density"].values()) == lost["total"]
    serialized = json.dumps(report, ensure_ascii=False)
    for secret in ("SENSITIVE_NAME", "rare", "조건길이열한글자", "한도", "대상 이름", "SENSITIVE_QUOTE", "new-item"):
        assert secret not in serialized


def test_item_loss_report_uses_all_base_runs_when_group_has_two(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()
    (chunks / "doc.chunks.json").write_text(json.dumps({"chunks": [{"chunk_id": "c", "text": "x"}]}), encoding="utf-8")
    item = _benefit("persist", ident="b")
    bases = []
    for i in range(2):
        path = tmp_path / f"b{i}"
        _write_run(path, [_row("c", [item])])
        bases.append(path)
    compare = tmp_path / "cmp"
    _write_run(compare, [_row("c")])
    report = build_report(bases, [compare], chunks)
    assert report["base_threshold_at_least"] == 2
    assert report["disappeared_candidates"]["total"] == 1


def test_item_loss_report_fuzzy_denominator_spelling_and_relation_matching(tmp_path):
    chunks = tmp_path / "chunks"
    chunks.mkdir()
    (chunks / "doc.chunks.json").write_text(json.dumps({"chunks": [{"chunk_id": "c", "text": "x"}]}), encoding="utf-8")
    stable = _benefit("Annual discount", "DISCOUNT", "b")
    lost = _benefit("merchant reward", "POINT", "lost")
    bases = []
    for i in range(4):
        path = tmp_path / f"base{i}"
        _write_run(path, [_row("c", [stable, lost], relations=[{"source": "b", "target": "lost", "type": "APPLIES_TO"}])])
        bases.append(path)
    compare = tmp_path / "compare"
    renamed = _benefit("Annual discount benefit", "DISCOUNT", "renamed")
    renamed_lost = _benefit("merchant rewards", "POINT", "renamed-lost")
    _write_run(compare, [_row("c", [renamed, renamed_lost], relations=[{"source": "renamed", "target": "renamed-lost", "type": "APPLIES_TO"}])])

    exact = build_report(bases, [compare], chunks)
    fuzzy = build_report(bases, [compare], chunks, fuzzy=True)
    assert exact["stable_items"]["total"] == 3
    assert exact["stable_items"]["by_section"]["benefits"] == 2
    assert exact["disappeared_candidates"]["total"] == 3
    assert fuzzy["disappeared_candidates"]["total"] == 3
    assert fuzzy["spelling_difference_candidates"]["total"] == 3
    assert fuzzy["genuine_disappeared_candidates"]["total"] == 0
    assert fuzzy["fuzzy_matched_compare_only_added"]["total"] == 3
    assert fuzzy["disappeared_candidate_rates"]["by_section"]["benefits"] == 1.0
    serialized = json.dumps(fuzzy, ensure_ascii=False)
    for secret in ("Annual discount", "Annual discount benefit", "merchant reward", "SENSITIVE_QUOTE"):
        assert secret not in serialized
