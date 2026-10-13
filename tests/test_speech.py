"""Exercise the public speech workflow without loading or downloading a model."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import gradio as gr
import numpy as np
import soundfile as sf

import app
from voice_engine import split_script


class FakeEngine:
    """Record requests and return small, reproducible waveforms."""

    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def create(self, text, *, voice, speed, lang):
        self.calls.append((text, voice, speed, lang))
        if len(self.calls) == self.fail_on:
            raise RuntimeError("Simulated synthesis failure")
        return np.full(24, 0.25, dtype=np.float32), 24_000


class SpeechWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.output_dir = Path(temporary.name) / "recordings"
        output_patch = patch.object(app, "OUTPUT_DIR", self.output_dir)
        output_patch.start()
        self.addCleanup(output_patch.stop)
        self.engine = FakeEngine()
        engine_patch = patch.object(app, "get_engine", return_value=self.engine)
        self.load_engine = engine_patch.start()
        self.addCleanup(engine_patch.stop)
        self.progress = Mock()

    def synthesize(self, text, character="heart", speed=1.0, pause_ms=220):
        return app.synthesize(text, character, speed, pause_ms, self.progress)

    def test_invalid_public_inputs_fail_before_loading_engine(self):
        invalid_requests = [
            (None, "heart", 1, 220),
            (123, "heart", 1, 220),
            ("   \n\t", "heart", 1, 220),
            ("a" * 20_001, "heart", 1, 220),
            ("Hello", "unknown", 1, 220),
            ("Hello", "af_heart", 1, 220),
            ("Hello", None, 1, 220),
            ("Hello", "heart", 0.749, 220),
            ("Hello", "heart", 1.501, 220),
            ("Hello", "heart", float("nan"), 220),
            ("Hello", "heart", float("inf"), 220),
            ("Hello", "heart", float("-inf"), 220),
            ("Hello", "heart", "invalid", 220),
            ("Hello", "heart", None, 220),
            ("Hello", "heart", 1, -0.001),
            ("Hello", "heart", 1, 1_000.001),
            ("Hello", "heart", 1, float("nan")),
            ("Hello", "heart", 1, float("inf")),
            ("Hello", "heart", 1, float("-inf")),
            ("Hello", "heart", 1, "invalid"),
            ("Hello", "heart", 1, None),
        ]
        for index, request in enumerate(invalid_requests):
            with self.subTest(request=index):
                with self.assertRaises(gr.Error):
                    self.synthesize(*request)
                self.load_engine.assert_not_called()
                self.assertFalse(self.output_dir.exists())

    def test_six_thousand_character_script_reaches_engine_in_full(self):
        script = " ".join([f"w{index:04d}" for index in range(999)] + ["ending"])
        self.assertEqual(len(script), 6_000)

        audio_path, download_path, status = self.synthesize(script, pause_ms=0)

        self.assertGreater(len(self.engine.calls), 1)
        self.assertEqual(" ".join(call[0] for call in self.engine.calls), script)
        self.assertEqual(audio_path, download_path)
        self.assertTrue(Path(audio_path).is_file())
        self.assertIn("6,000 characters", status)

    def test_each_character_selects_its_actual_voice_and_language(self):
        expected = {
            "heart": ("af_heart", "en-us"),
            "bella": ("af_bella", "en-us"),
            "nicole": ("af_nicole", "en-us"),
            "sarah": ("af_sarah", "en-us"),
            "sky": ("af_sky", "en-us"),
            "adam": ("am_adam", "en-us"),
            "michael": ("am_michael", "en-us"),
            "fenrir": ("am_fenrir", "en-us"),
            "emma": ("bf_emma", "en-gb"),
            "isabella": ("bf_isabella", "en-gb"),
            "george": ("bm_george", "en-gb"),
            "fable": ("bm_fable", "en-gb"),
        }
        for character, (voice, language) in expected.items():
            with self.subTest(character=character):
                self.engine.calls.clear()
                self.synthesize("Read this selected character.", character, speed=1.25)
                self.assertEqual(
                    self.engine.calls,
                    [("Read this selected character.", voice, 1.25, language)],
                )

    def test_wav_format_and_pauses_only_between_segments(self):
        audio_path, download_path, _ = self.synthesize(
            "First sentence. Second sentence! Third sentence?", pause_ms=125
        )

        information = sf.info(audio_path)
        self.assertEqual(information.format, "WAV")
        self.assertEqual(information.subtype, "PCM_16")
        self.assertEqual(information.channels, 1)
        self.assertEqual(information.samplerate, 24_000)
        self.assertEqual(information.frames, 3 * 24 + 2 * 3_000)
        samples, sample_rate = sf.read(audio_path, dtype="int16")
        self.assertEqual(sample_rate, 24_000)
        expected = np.concatenate([
            np.full(24, 8_192, dtype=np.int16),
            np.zeros(3_000, dtype=np.int16),
            np.full(24, 8_192, dtype=np.int16),
            np.zeros(3_000, dtype=np.int16),
            np.full(24, 8_192, dtype=np.int16),
        ])
        np.testing.assert_array_equal(samples, expected)
        self.assertEqual(download_path, audio_path)
        self.assertFalse(list(self.output_dir.glob("*.part.wav")))

    def test_zero_pause_does_not_insert_silence(self):
        audio_path, _, _ = self.synthesize("First. Second.", pause_ms=0)
        samples, _ = sf.read(audio_path, dtype="int16")
        np.testing.assert_array_equal(samples, np.full(48, 8_192, dtype=np.int16))

    def test_later_synthesis_failure_removes_partial_recording(self):
        self.engine.fail_on = 2

        with self.assertLogs(app.logger, level="ERROR"):
            with self.assertRaises(gr.Error):
                self.synthesize("Successful first part. Failing second part. Unreached third part.")

        self.assertEqual(len(self.engine.calls), 2)
        self.assertEqual(list(self.output_dir.iterdir()), [])


class ScriptSplittingTests(unittest.TestCase):
    def test_paragraphs_and_long_sentences_preserve_all_words(self):
        script = (
            "Opening paragraph.\n\n"
            + " ".join(f"word{index}" for index in range(200))
            + "!\nClosing paragraph? Final line."
        )

        chunks = split_script(script)

        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(0 < len(chunk) <= 280 for chunk in chunks))
        self.assertEqual(" ".join(chunks).split(), script.split())

    def test_oversized_token_preserves_every_character_without_truncation(self):
        token = "abcdefghijklmnopqrstuvwxyz" * 35
        chunks = split_script(f"Before {token} after.")

        self.assertEqual(chunks[0], "Before")
        self.assertEqual(chunks[-1], "after.")
        self.assertEqual("".join(chunks[1:-1]), token)
        self.assertTrue(all(0 < len(chunk) <= 280 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
