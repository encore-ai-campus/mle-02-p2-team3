import json
import re
from pathlib import Path


FILE_PIPELINE = Path(__file__).parents[1] / "file_pipeline"
NOTEBOOKS = FILE_PIPELINE / "notebooks"
MODULE_LIST = NOTEBOOKS / "모듈-점검-목록.md"


def _modules():
    return {
        path.stem
        for directory in (FILE_PIPELINE / "extraction", FILE_PIPELINE / "graph")
        for path in directory.glob("*.py")
        if path.name != "__init__.py"
    }


def _entries():
    entries = {}
    for line in MODULE_LIST.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"\|\s*([^|]+?)\s*\|\s*(있음|예정)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", line)
        if match:
            module, status, notebook, title = (part.strip() for part in match.groups())
            entries[module] = (status, notebook, title)
    return entries


def test_every_extraction_and_graph_module_is_listed():
    assert _modules() == set(_entries())


def test_listed_notebooks_exist_and_have_empty_code_outputs():
    for module, (status, notebook, _title) in _entries().items():
        if status == "예정":
            continue
        path = NOTEBOOKS / notebook
        document = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(document.get("cells"), list), module
        assert all(not cell.get("outputs", []) for cell in document["cells"] if cell.get("cell_type") == "code"), module


def test_all_notebooks_have_empty_outputs():
    for path in NOTEBOOKS.glob("*.ipynb"):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert all(not cell.get("outputs", []) for cell in document["cells"] if cell.get("cell_type") == "code"), path.name
