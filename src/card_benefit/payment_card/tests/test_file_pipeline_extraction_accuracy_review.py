import json
from pathlib import Path

import pytest

from payment_card.file_pipeline.extraction.accuracy_review import main, prepare, tally


def _inputs(tmp_path, lengths=(100, 1100, 2100, 4100)):
    chunks = tmp_path / "chunks"
    chunks.mkdir()
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    chunk_rows = []
    for index, length in enumerate(lengths):
        chunk_id = f"chunk-{index}"
        chunk_rows.append({"chunk_id": chunk_id, "text": "s" * length, "page_no": index + 1})
        result = {"chunk_id": chunk_id, "page_no": index + 1, "chunk_length": length,
                  "extraction": {"benefits": [{"name": "synthetic benefit", "rate": "10%", "method": "할인"}],
                                 "conditions": [], "limits": [], "targets": [], "relations": []}}
        (result_dir / f"{chunk_id}.result.json").write_text(json.dumps(result), encoding="utf-8")
    (chunks / "sample.chunks.json").write_text(json.dumps({"chunks": chunk_rows}), encoding="utf-8")
    return result_dir, chunks


def test_prepare_samples_reproducibly_by_length_bin_and_seed(tmp_path):
    results, chunks = _inputs(tmp_path, (100, 200, 300, 400, 1100, 1200, 1300, 1400,
                                          2100, 2200, 2300, 2400, 4100, 4200, 4300, 4400))
    first = prepare(results, chunks, tmp_path / "one", size=8, seed=41)
    again = prepare(results, chunks, tmp_path / "two", size=8, seed=41)
    changed = prepare(results, chunks, tmp_path / "three", size=8, seed=42)
    assert first["selected"] == again["selected"]
    assert first["selected"] != changed["selected"]
    assert first["bin_counts"] == {"<=999": 2, "1000-1999": 2, "2000-3999": 2, ">=4000": 2}


def test_prepare_handles_empty_bins_and_caps_to_population(tmp_path):
    results, chunks = _inputs(tmp_path, (100, 200, 300))
    prepared = prepare(results, chunks, tmp_path / "review", size=10, seed=1)
    assert len(prepared["selected"]) == 3
    assert prepared["bin_counts"] == {"<=999": 3, "1000-1999": 0, "2000-3999": 0, ">=4000": 0}


def test_prepare_rejects_repo_output_and_protects_existing_files(tmp_path):
    results, chunks = _inputs(tmp_path)
    with pytest.raises(ValueError, match="저장소 밖"):
        prepare(results, chunks, Path(__file__).parents[3] / "unsafe")
    output = tmp_path / "review"
    prepare(results, chunks, output)
    with pytest.raises(FileExistsError):
        prepare(results, chunks, output)
    stale = output / "accuracy_view" / "99_old.txt"
    stale.write_text("old", encoding="utf-8")
    prepare(results, chunks, output, overwrite=True)
    assert not stale.exists()


def test_prepare_sanitizes_chunk_id_in_view_filename(tmp_path):
    results, chunks = _inputs(tmp_path, (100,))
    result_path = results / "chunk-0.result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")); result["chunk_id"] = "a/../unsafe"
    result_path.unlink(); (results / "unsafe.result.json").write_text(json.dumps(result), encoding="utf-8")
    chunk_path = chunks / "sample.chunks.json"
    data = json.loads(chunk_path.read_text(encoding="utf-8")); data["chunks"][0]["chunk_id"] = "a/../unsafe"
    chunk_path.write_text(json.dumps(data), encoding="utf-8")
    prepared = prepare(results, chunks, tmp_path / "review")
    assert Path(prepared["views"][0]).name == "01_a____unsafe.txt"


def test_tally_reads_verdict_only_and_json_excludes_memo(tmp_path, capsys):
    sheet = tmp_path / "accuracy_verdicts.md"
    sheet.write_text("""| N | chunk_id | page | length | counts | view | verdict | memo |
|---|---|---|---|---|---|---|---|
| 1 | alpha-long-chunk-id | 3 | 4 | b1 | a.txt | [X] 맞음 [ ] 틀림 [ ] 일부 누락 | [x] 틀림 |
| 2 | beta | 5 | 4 | b1 | b.txt | [ x ] 틀림 [ ] 맞음 | note with [x] 일부 누락 |
| 3 | gamma | 6 | 4 | b1 | c.txt | [✓] 일부 누락 [ ] 맞음 | secret source wording |
| 4 | delta | 7 | 4 | b1 | d.txt | [v] 맞음 [x] 틀림 | memo |
| 5 | epsilon | 8 | 4 | b1 | e.txt | [ ] 맞음 [ ] 틀림 [ ] 일부 누락 | undecided |
""", encoding="utf-8")
    result = tally(sheet)
    assert result["counts"] == {"맞음": 1, "틀림": 1, "일부 누락": 1, "미판정": 1, "중복": 1}
    assert result["precision"] == 1 / 3
    assert result["wrong"] == [("beta", "5")]
    json_out = tmp_path / "decisions.json"
    main(["tally", "--sheet", str(sheet), "--json-out", str(json_out)])
    out = json_out.read_text(encoding="utf-8")
    assert "secret source wording" not in out and "memo" not in out and "beta" in out
    assert len(capsys.readouterr().out.splitlines()) == 3
