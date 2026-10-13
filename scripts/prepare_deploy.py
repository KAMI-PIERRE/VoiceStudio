"""Package only deployable source/assets, excluding credentials and local recordings."""
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "app.py", "characters.py", "voice_engine.py", "studio_ui.py", "runtime_config.py",
    "requirements.txt", "packages.txt", "Dockerfile", ".dockerignore", ".gitignore",
    "README.md", "DEPLOYMENT.md",
)


def main():
    files = [ROOT / filename for filename in SOURCE_FILES]
    files += sorted(path for path in (ROOT / "assets").rglob("*") if path.is_file() and path.suffix.lower() in {".svg", ".png", ".ico"})
    for path in files:
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
            raise RuntimeError(f"A deployment source is missing or outside the project: {path.name}")
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    version = digest.hexdigest()[:12]
    destination = ROOT / "deployment" / f"voice-studio-{version}"
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.resolve().is_relative_to(ROOT / "deployment"):
        raise RuntimeError("The deployment destination must remain inside this project.")
    expected = {path.relative_to(ROOT).as_posix() for path in files}
    existing = {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file()}
    if existing - expected:
        raise RuntimeError("The deployment folder contains unexpected files; use a clean destination.")
    for path in files:
        target = destination / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, path.relative_to(ROOT).as_posix())
    print(f"Deployment folder: {destination}")
    print(f"Deployment ZIP: {archive}")
    print(f"Included {len(files)} files. Local environments, recordings, caches, and credentials are excluded.")


if __name__ == "__main__":
    main()
