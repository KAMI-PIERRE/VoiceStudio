"""Download a verified Kokoro library once, then synthesize entirely locally."""
from functools import lru_cache
import hashlib
import logging
from pathlib import Path
import re
from threading import Lock
import urllib.request

from runtime_config import get_settings

MODEL_DIR = get_settings().model_dir
RELEASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1"
ASSETS = {
    "kokoro-v1.0.int8.onnx": "ae315a79b623f244700e4afb9246c46a26066782e049ba174bf3ba433970ee9c",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
_download_lock = Lock()
logger = logging.getLogger(__name__)


def _digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def download_assets():
    """Use fixed release files, verify SHA-256, and never publish partial downloads."""
    with _download_lock:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        for filename, checksum in ASSETS.items():
            destination = MODEL_DIR / filename
            if destination.is_file() and _digest(destination) == checksum:
                logger.info("Verified %s", filename)
                continue
            partial = destination.with_suffix(destination.suffix + ".part")
            request = urllib.request.Request(
                f"{RELEASE_URL}/{filename}",
                headers={"User-Agent": "VoiceStudio/1.0"},
            )
            logger.info("Downloading %s (first use only)", filename)
            try:
                with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as output:
                    total = int(response.headers.get("Content-Length", 0))
                    downloaded = 0
                    last_percent = -10
                    while block := response.read(1024 * 1024):
                        output.write(block)
                        downloaded += len(block)
                        percent = int(downloaded * 100 / total) if total else 0
                        if total and percent >= last_percent + 10:
                            logger.info("%s: %d%%", filename, percent)
                            last_percent = percent
                if _digest(partial) != checksum:
                    raise RuntimeError(f"Checksum verification failed for {filename}.")
                partial.replace(destination)
            except Exception:
                partial.unlink(missing_ok=True)
                raise
            logger.info("Downloaded and verified %s", filename)
    return MODEL_DIR


@lru_cache(maxsize=1)
def get_engine():
    from kokoro_onnx import Kokoro
    from characters import CHARACTERS
    model_dir = download_assets()
    logger.info("Loading the local character voice library")
    engine = Kokoro(str(model_dir / "kokoro-v1.0.int8.onnx"), str(model_dir / "voices-v1.0.bin"))
    available = set(engine.get_voices())
    missing = {character["voice"] for character in CHARACTERS.values()} - available
    if missing:
        raise RuntimeError(f"The voice library is missing: {', '.join(sorted(missing))}")
    return engine


def split_script(text, limit=280):
    """Prefer sentence/paragraph boundaries; retain all words in oversized sentences."""
    chunks = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip()):
        current = ""
        for word in sentence.split():
            if len(word) > limit:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(word[start:start + limit] for start in range(0, len(word), limit))
                continue
            proposed = f"{current} {word}".strip()
            if len(proposed) > limit and current:
                chunks.append(current)
                current = word
            else:
                current = proposed
        if current:
            chunks.append(current)
    return chunks
