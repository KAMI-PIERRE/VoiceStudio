"""Runtime defaults for the local studio and hosted Python deployments."""
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

PROJECT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class RuntimeSettings:
    hosted: bool
    host: str
    port: int
    output_dir: Path
    model_dir: Path
    retention_seconds: int


def get_settings(environ=None):
    env = os.environ if environ is None else environ
    hosted = env.get("VOICE_STUDIO_HOSTED") == "1" or bool(env.get("SPACE_ID")) or env.get("RENDER") == "true"
    host = env.get("GRADIO_SERVER_NAME") or ("0.0.0.0" if hosted else "127.0.0.1")
    port = int(env.get("PORT") or env.get("GRADIO_SERVER_PORT") or "7860")
    if not 1 <= port <= 65_535:
        raise ValueError("The server port must be between 1 and 65535.")
    retention = int(env.get("VOICE_STUDIO_RETENTION_SECONDS", "86400" if hosted else "0"))
    if retention < 0:
        raise ValueError("VOICE_STUDIO_RETENTION_SECONDS cannot be negative.")
    default_output = Path(tempfile.gettempdir()) / "voice-studio" / "outputs" if hosted else PROJECT_DIR / "outputs"
    return RuntimeSettings(
        hosted=hosted,
        host=host,
        port=port,
        output_dir=Path(env.get("VOICE_STUDIO_OUTPUT_DIR") or default_output).expanduser().resolve(),
        model_dir=Path(env.get("VOICE_STUDIO_MODEL_DIR") or PROJECT_DIR / ".models" / "kokoro").expanduser().resolve(),
        retention_seconds=retention,
    )
