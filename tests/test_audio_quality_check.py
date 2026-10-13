"""Regression tests for the public WAV inspection CLI.

All test audio is generated in memory; no recordings or client data are used.
Run with: python -m unittest discover -s tests -v
"""

import contextlib
import io
import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from audio_quality_check import analyze_audio, dbfs


class AudioQualityCheckTests(unittest.TestCase):
    def make_wav(self, directory, samples, *, channels=1, rate=44100, width=2):
        path = Path(directory) / "sample.wav"
        with wave.open(str(path), "wb") as output:
            output.setnchannels(channels)
            output.setsampwidth(width)
            output.setframerate(rate)
            output.writeframes(samples)
        return path

    def capture_report(self, path):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            analyze_audio(path)
        return output.getvalue()

    def test_dbfs_converts_amplitude(self):
        self.assertAlmostEqual(dbfs(0.5), -6.0206, places=3)
        self.assertEqual(dbfs(0), float("-inf"))

    def test_silent_8bit_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_wav(directory, bytes([128] * 100), width=1)
            report = self.capture_report(path)
        self.assertIn("Bit depth: 8 bit", report)
        self.assertIn("Peak level: -inf dBFS", report)
        self.assertIn("RMS level: -inf dBFS", report)
        self.assertIn("Samples near clipping: 0", report)

    def test_16bit_peak_rms_and_clipping(self):
        data = struct.pack("<4h", 0, 16384, -16384, 32767)
        with tempfile.TemporaryDirectory() as directory:
            report = self.capture_report(self.make_wav(directory, data))
        self.assertIn("Peak level: -0.00 dBFS", report)
        self.assertIn("Samples near clipping: 1", report)
        self.assertIn("Channels: 1", report)

    def test_24bit_pcm(self):
        data = b"".join(x.to_bytes(3, "little", signed=True) for x in (0, 4194304, -4194304))
        with tempfile.TemporaryDirectory() as directory:
            report = self.capture_report(self.make_wav(directory, data, width=3))
        self.assertIn("Bit depth: 24 bit", report)
        self.assertIn("Peak level: -6.02 dBFS", report)

    def test_32bit_pcm(self):
        data = struct.pack("<3i", 0, 1073741824, -1073741824)
        with tempfile.TemporaryDirectory() as directory:
            report = self.capture_report(self.make_wav(directory, data, width=4))
        self.assertIn("Bit depth: 32 bit", report)
        self.assertIn("Peak level: -6.02 dBFS", report)

    def test_stereo_metadata(self):
        data = struct.pack("<8h", 0, 0, 200, -200, 300, -300, 0, 0)
        with tempfile.TemporaryDirectory() as directory:
            report = self.capture_report(self.make_wav(directory, data, channels=2, rate=48000))
        self.assertIn("Channels: 2", report)
        self.assertIn("Sample rate: 48000 Hz", report)
        self.assertIn("Duration: 0.00 seconds", report)

    def test_missing_file_is_not_silently_accepted(self):
        with self.assertRaises(FileNotFoundError):
            self.capture_report(Path("file_that_does_not_exist.wav"))


if __name__ == "__main__":
    unittest.main()
