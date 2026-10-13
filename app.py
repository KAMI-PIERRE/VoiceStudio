"""Voice Studio: a local character voice workspace with downloadable WAV audio."""
import argparse
import hashlib
import logging
import math
from pathlib import Path
import re
import time
import uuid

import gradio as gr
import numpy as np
import soundfile as sf

from characters import CHARACTERS, DEFAULT_CHARACTER
from voice_engine import download_assets, get_engine, split_script
from runtime_config import get_settings

MAX_CHARACTERS = 20_000
SETTINGS = get_settings()
OUTPUT_DIR = SETTINGS.output_dir
logger = logging.getLogger(__name__)


def cleanup_recordings(now=None):
    """Expire completed hosted recordings; local recordings remain saved by default."""
    if not SETTINGS.retention_seconds or not OUTPUT_DIR.is_dir():
        return
    cutoff = (time.time() if now is None else now) - SETTINGS.retention_seconds
    for path in OUTPUT_DIR.glob("*.wav"):
        if not re.fullmatch(r"[a-z]+-[0-9a-f]{12}\.wav", path.name) or path.name.split("-", 1)[0] not in CHARACTERS:
            continue
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            logger.warning("Could not expire recording %s", path.name)


def validate_request(text, character_id, speed, pause_ms):
    """Validate public API inputs as well as the controls shown in the studio."""
    if not isinstance(text, str) or not text.strip():
        raise gr.Error("Add some English text to your script first.")
    if len(text) > MAX_CHARACTERS:
        raise gr.Error(f"Keep your script within {MAX_CHARACTERS:,} characters.")
    if not isinstance(character_id, str) or character_id not in CHARACTERS:
        raise gr.Error("Choose a character from the voice library.")
    try:
        speed = float(speed)
        pause_ms = float(pause_ms)
    except (TypeError, ValueError):
        raise gr.Error("Choose a valid speaking speed and pause length.") from None
    if not math.isfinite(speed) or not 0.75 <= speed <= 1.5:
        raise gr.Error("Speaking speed must be between 0.75 and 1.50.")
    if not math.isfinite(pause_ms) or not 0 <= pause_ms <= 1_000:
        raise gr.Error("Pauses must be between 0 and 1,000 milliseconds.")
    return text.strip(), CHARACTERS[character_id], speed, pause_ms


def synthesize(
    text: str,
    character_id: str = DEFAULT_CHARACTER,
    speed: float = 1.0,
    pause_ms: float = 220,
    progress=gr.Progress(),
):
    """Write each generated segment immediately, keeping long scripts memory bounded."""
    text, character, speed, pause_ms = validate_request(text, character_id, speed, pause_ms)
    segments = split_script(text)
    if not segments:
        raise gr.Error("Add words or numbers to your English script.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_recordings()
    basename = f"{character_id}-{uuid.uuid4().hex[:12]}"
    partial_path = OUTPUT_DIR / f"{basename}.part.wav"
    final_path = OUTPUT_DIR / f"{basename}.wav"
    started = time.perf_counter()
    progress(0, desc="Preparing your character. First use downloads the voice library.")
    try:
        engine = get_engine()
        frames = 0
        sample_rate = 24_000
        with sf.SoundFile(partial_path, mode="w", samplerate=sample_rate,
                          channels=1, subtype="PCM_16") as output:
            for index, segment in enumerate(segments):
                progress(index / len(segments), desc=f"Recording part {index + 1} of {len(segments)}")
                samples, rate = engine.create(
                    segment, voice=character["voice"], speed=speed,
                    lang=character["language"],
                )
                waveform = np.asarray(samples, dtype=np.float32).reshape(-1)
                if rate != sample_rate or not waveform.size or not np.isfinite(waveform).all():
                    raise RuntimeError("The voice engine returned invalid audio.")
                if index and pause_ms:
                    silence = np.zeros(round(sample_rate * pause_ms / 1_000), dtype=np.float32)
                    output.write(silence)
                    frames += silence.size
                output.write(np.clip(waveform, -1, 1))
                frames += waveform.size
        partial_path.replace(final_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        logger.exception("Speech generation failed for character %s", character_id)
        raise gr.Error(
            "We couldn't finish this recording. On first use, check your internet "
            "connection so the voice library can download, then try again. "
            "Your script is still in the editor."
        ) from None
    progress(1, desc="Your recording is ready")
    duration = frames / sample_rate
    minutes, seconds = divmod(round(duration), 60)
    elapsed = time.perf_counter() - started
    status = (
        f"**Ready to listen** · {character['name']} · {minutes}:{seconds:02d} audio "
        f"· {len(text):,} characters · created in {elapsed:.1f}s"
    )
    return str(final_path), str(final_path), status


def create_demo():
    from studio_ui import build_interface
    return build_interface(
        synthesize, CHARACTERS, DEFAULT_CHARACTER, MAX_CHARACTERS,
        "English character voices" if SETTINGS.hosted else "Local voices · English",
        hosted=SETTINGS.hosted,
        retention_seconds=SETTINGS.retention_seconds,
    )


def main():
    parser = argparse.ArgumentParser(description="Run your local Voice Studio.")
    parser.add_argument("--download-model", action="store_true", help="Download and verify the voice library, then exit.")
    parser.add_argument("--host", default=SETTINGS.host, help="Bind address (localhost locally, all interfaces when hosted).")
    parser.add_argument("--port", type=int, default=SETTINGS.port, help="Server port (PORT/GRADIO_SERVER_PORT or 7860).")
    parser.add_argument("--open-browser", action="store_true", help="Open the studio in your default browser.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.download_model:
        download_assets()
        print("Voice library downloaded and verified. Start the studio with python app.py.")
        return
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_recordings()
    from studio_ui import CSS, THEME, LOGO_PATH
    favicon_path = LOGO_PATH.with_name("voice-studio-favicon.ico")
    favicon_version = hashlib.sha256(favicon_path.read_bytes()).hexdigest()[:12]
    demo = create_demo()
    demo.queue(default_concurrency_limit=1, max_size=8).launch(
        inbrowser=args.open_browser,
        server_name=args.host,
        server_port=args.port,
        theme=THEME,
        css=CSS,
        favicon_path=favicon_path,
        head=(
            '<link rel="icon" type="image/vnd.microsoft.icon" '
            'sizes="16x16 24x24 32x32 48x48 64x64 128x128 256x256" '
            f'href="/favicon.ico?v={favicon_version}">'
        ),
        show_error=False,
        footer_links=[],
        allowed_paths=[] if SETTINGS.hosted else [str(OUTPUT_DIR)],
    )


if __name__ == "__main__":
    main()
