"""Check real speech and downloads for every character against the running app."""
import hashlib
from pathlib import Path
import sys

import numpy as np
import soundfile as sf
from gradio_client import Client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from characters import CHARACTERS


def check_recording(result, character):
    audio_path, download_path, status = result
    info = sf.info(audio_path)
    samples, rate = sf.read(audio_path, dtype="float32")
    assert info.channels == 1 and rate == 24_000 and info.subtype == "PCM_16"
    assert len(samples) > rate / 2 and np.isfinite(samples).all()
    assert np.max(np.abs(samples)) > 0.0001, "Recording is silent"
    assert Path(download_path).is_file(), "Download did not produce a file"
    assert character["name"] in status, "Recording metadata identifies a different character"
    return hashlib.sha256(Path(audio_path).read_bytes()).hexdigest(), info.duration


def main():
    client = Client("http://127.0.0.1:7860/", verbose=False)
    hashes = set()
    for character_id, character in CHARACTERS.items():
        result = client.predict(
            "Welcome to Voice Studio.", character_id, 1.0, 220,
            api_name="/synthesize",
        )
        digest, duration = check_recording(result, character)
        hashes.add(digest)
        print(f"PASS {character['name']}: {duration:.2f}s, valid WAV and download", flush=True)
    assert len(hashes) == len(CHARACTERS), "Expected distinct recordings for each voice"
    preview = client.predict("george", 1.25, 100, api_name="/preview_voice")
    check_recording(preview, CHARACTERS["george"])
    assert "Voice preview" in preview[2]
    print("PASS voice preview with custom speed and pause settings", flush=True)
    print("All 12 character voices and preview passed real speech checks.", flush=True)


if __name__ == "__main__":
    main()
