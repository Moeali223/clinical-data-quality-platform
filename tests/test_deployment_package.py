import importlib.util
from pathlib import Path
from zipfile import ZipFile


def test_deployment_package_contains_only_runtime_inputs(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("package_deployment", root / "scripts/package_deployment.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    destination = tmp_path / "deployment.zip"
    module.package(destination)
    with ZipFile(destination) as archive:
        names = set(archive.namelist())
    assert {"requirements.txt", "pyproject.toml", "README.md", "src/clinical_data_quality/api.py"} <= names
    assert all(name.startswith("src/") or name in {"requirements.txt", "pyproject.toml", "README.md"} for name in names)
    assert not any(".env" in name or "__pycache__" in name or "tests/" in name for name in names)
