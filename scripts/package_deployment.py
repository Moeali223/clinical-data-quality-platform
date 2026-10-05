"""Create an allowlisted Azure ZIP; never include environments or credentials."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def package(destination: Path) -> None:
    inputs = [ROOT / name for name in ("pyproject.toml", "requirements.txt", "README.md")]
    inputs += sorted((ROOT / "src").rglob("*.py"))
    inputs = [path for path in inputs if "__pycache__" not in path.parts]
    if any(path.is_symlink() for path in inputs):
        raise ValueError("Deployment inputs must not be symlinks.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in inputs:
            archive.write(path, path.relative_to(ROOT))


if __name__ == "__main__":
    destination = ROOT / "dist" / "azure-deployment.zip"
    package(destination)
    print(f"Created {destination}")
