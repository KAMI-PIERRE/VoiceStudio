"""Package a built browser edition for free Hugging Face Static hosting."""
import hashlib
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BROWSER = ROOT / "browser"


def main():
    built = BROWSER / "dist"
    if not (built / "index.html").is_file():
        raise SystemExit("Build first: cd browser; npm run build")
    files = sorted(path for path in built.rglob("*") if path.is_file())
    extensions = {".html", ".css", ".js", ".mjs", ".wasm", ".svg", ".png", ".ico"}
    for path in files:
        if path.is_symlink() or not path.resolve().is_relative_to(built.resolve()) or path.suffix.lower() not in extensions:
            raise RuntimeError(f"Unexpected file in the static build: {path.name}")
    contents = {path.relative_to(built).as_posix(): path.read_bytes() for path in files}
    contents["README.md"] = (BROWSER / "README.md").read_bytes()
    digest = hashlib.sha256()
    for name, data in sorted(contents.items()):
        digest.update(name.encode())
        digest.update(data)
    destination = ROOT / "deployment" / f"voice-studio-static-{digest.hexdigest()[:12]}"
    destination.mkdir(parents=True, exist_ok=True)
    if not destination.resolve().is_relative_to((ROOT / "deployment").resolve()):
        raise RuntimeError("The deployment destination must stay within this project.")
    existing = {path.relative_to(destination).as_posix() for path in destination.rglob("*") if path.is_file()}
    if existing - contents.keys():
        raise RuntimeError("Unexpected files already exist in the deployment folder.")
    for name, data in contents.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive = destination.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in contents.items():
            bundle.writestr(name, data)
    print(f"Static deployment folder: {destination}")
    print(f"Static deployment ZIP: {archive}")
    print(f"Included {len(contents)} files; no Python server, recordings, credentials, or local model cache.")


if __name__ == "__main__":
    main()
