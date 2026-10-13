"""Verify deployment settings and safe expiration of generated recordings."""

from dataclasses import replace
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app
from runtime_config import get_settings


class RuntimeSettingsTests(unittest.TestCase):
    def test_local_defaults_keep_existing_paths_and_recordings(self):
        settings = get_settings({})
        project_dir = Path(__file__).resolve().parents[1]

        self.assertFalse(settings.hosted)
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 7860)
        self.assertEqual(settings.output_dir, project_dir / "outputs")
        self.assertEqual(settings.model_dir, project_dir / ".models" / "kokoro")
        self.assertEqual(settings.retention_seconds, 0)

    def test_hosted_platforms_bind_all_interfaces_and_expire_recordings(self):
        for environment in (
            {"SPACE_ID": "account/voice-studio"},
            {"VOICE_STUDIO_HOSTED": "1"},
            {"RENDER": "true"},
        ):
            with self.subTest(environment=environment):
                settings = get_settings(environment)
                self.assertTrue(settings.hosted)
                self.assertEqual(settings.host, "0.0.0.0")
                self.assertEqual(settings.port, 7860)
                self.assertEqual(settings.retention_seconds, 86_400)
                self.assertEqual(
                    settings.output_dir,
                    (Path(tempfile.gettempdir()) / "voice-studio" / "outputs").resolve(),
                )

    def test_false_hosted_flags_keep_local_defaults(self):
        settings = get_settings({"VOICE_STUDIO_HOSTED": "0", "SPACE_ID": "", "RENDER": "false"})
        self.assertFalse(settings.hosted)
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.retention_seconds, 0)

    def test_platform_port_overrides_gradio_port(self):
        settings = get_settings({"SPACE_ID": "account/studio", "PORT": "8080", "GRADIO_SERVER_PORT": "7861"})
        self.assertEqual(settings.port, 8080)
        self.assertEqual(get_settings({"GRADIO_SERVER_PORT": "7861"}).port, 7861)
        self.assertEqual(get_settings({"PORT": "", "GRADIO_SERVER_PORT": "7861"}).port, 7861)

    def test_custom_paths_host_and_retention_are_used(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "recordings"
            model_dir = Path(directory) / "models"
            settings = get_settings({
                "VOICE_STUDIO_HOSTED": "1",
                "VOICE_STUDIO_OUTPUT_DIR": str(output_dir),
                "VOICE_STUDIO_MODEL_DIR": str(model_dir),
                "VOICE_STUDIO_RETENTION_SECONDS": "7200",
                "GRADIO_SERVER_NAME": "127.0.0.2",
            })

            self.assertEqual(settings.output_dir, output_dir.resolve())
            self.assertEqual(settings.model_dir, model_dir.resolve())
            self.assertEqual(settings.retention_seconds, 7200)
            self.assertEqual(settings.host, "127.0.0.2")
            self.assertFalse(output_dir.exists())
            self.assertFalse(model_dir.exists())

    def test_invalid_port_values_are_rejected(self):
        for variable in ("PORT", "GRADIO_SERVER_PORT"):
            for value in ("0", "-1", "65536", "not-a-port", "7860.5"):
                with self.subTest(variable=variable, value=value):
                    with self.assertRaises(ValueError):
                        get_settings({variable: value})
        for value in ("1", "65535"):
            with self.subTest(valid_boundary=value):
                self.assertEqual(get_settings({"PORT": value}).port, int(value))

    def test_negative_retention_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "VOICE_STUDIO_RETENTION_SECONDS.*negative"):
            get_settings({"VOICE_STUDIO_RETENTION_SECONDS": "-1"})
        settings = get_settings({"VOICE_STUDIO_HOSTED": "1", "VOICE_STUDIO_RETENTION_SECONDS": "0"})
        self.assertEqual(settings.retention_seconds, 0)


class RecordingExpirationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output_dir = Path(temporary.name)
        self.now = 2_000_000_000
        self.retention = 3_600
        settings = replace(
            get_settings({}),
            hosted=True,
            output_dir=self.output_dir,
            retention_seconds=self.retention,
        )
        patches = patch.multiple(app, SETTINGS=settings, OUTPUT_DIR=self.output_dir)
        patches.start()
        self.addCleanup(patches.stop)

    def create_file(self, filename, modified):
        path = self.output_dir / filename
        path.write_bytes(b"test recording")
        os.utime(path, (modified, modified))
        return path

    def test_only_expired_complete_generated_recordings_are_removed(self):
        expired_time = self.now - self.retention - 1
        expired = self.create_file("heart-012345abcdef.wav", expired_time)
        recent = self.create_file("bella-abcdef012345.wav", self.now - 60)
        boundary = self.create_file("emma-0123456789ab.wav", self.now - self.retention)
        active = self.create_file("adam-0123456789ab.part.wav", expired_time)
        user_audio = self.create_file("my-personal-recording.wav", expired_time)
        user_audio_matching_uuid = self.create_file("meeting-012345abcdef.wav", expired_time)
        unrelated = self.create_file("notes.txt", expired_time)
        malformed = self.create_file("heart-01234.wav", expired_time)

        app.cleanup_recordings(now=self.now)

        self.assertFalse(expired.exists())
        for path in (recent, boundary, active, user_audio, user_audio_matching_uuid, unrelated, malformed):
            with self.subTest(preserved=path.name):
                self.assertEqual(path.read_bytes(), b"test recording")

    def test_disabled_retention_preserves_even_expired_generated_recordings(self):
        recording = self.create_file("michael-012345abcdef.wav", self.now - 100_000)
        settings = replace(app.SETTINGS, retention_seconds=0)

        with patch.object(app, "SETTINGS", settings):
            app.cleanup_recordings(now=self.now)

        self.assertTrue(recording.exists())

    def test_missing_output_directory_is_safe(self):
        missing_dir = self.output_dir / "not-created"
        with patch.object(app, "OUTPUT_DIR", missing_dir):
            app.cleanup_recordings(now=self.now)
        self.assertFalse(missing_dir.exists())


if __name__ == "__main__":
    unittest.main()
