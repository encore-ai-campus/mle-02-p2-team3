import json
import re
from pathlib import Path


NOTEBOOK = Path(__file__).resolve().parents[1] / "file_pipeline" / "notebooks" / "neo4j_sample_check.ipynb"


def _cells():
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]


def test_notebook_is_unexecuted_and_safe_by_default():
    cells = _cells()
    code_cells = [cell for cell in cells if cell["cell_type"] == "code"]
    sources = ["".join(cell["source"]) for cell in code_cells]
    full = "\n".join(sources)
    assert all(not cell["outputs"] and cell["execution_count"] is None for cell in code_cells)
    assert re.search(r"WRITE\s*=\s*False", full)
    assert re.search(r"ALLOW_REMOTE\s*=\s*False", full)
    assert re.search(r"CONFIRM_DELETE\s*=\s*False", full)
    assert full.count("DETACH DELETE") == 1
    delete_cell = next(source for source in sources if "DETACH DELETE" in source)
    assert "CONFIRM_DELETE" in delete_cell
    assert "DETACH DELETE" not in "\n".join(source for source in sources if source != delete_cell)
    for source in sources:
        assert not re.search(r"\b(?:print|display)\s*\([^\n]*(?:NEO4J_PASSWORD|NEO4J_URI|NEO4J_USERNAME|password)", source, re.I)
    assert not re.search(r"\bMATCH\s*\(\s*n\s*\)", "\n".join(source for source in sources if "DETACH DELETE" not in source))
    assert not re.search(r"\bimport\s+pyvis|\bfrom\s+pyvis", full)
    for source in sources:
        compile(source, str(NOTEBOOK), "exec")
