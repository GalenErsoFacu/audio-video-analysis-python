"""Synthetic, non-confidential tests for audio_timeline_analysis.py."""
import contextlib
import csv
import io
import math
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import wave

import audio_timeline_analysis as analyzer


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
class AudioTimelineTests(unittest.TestCase):
    @staticmethod
    def make_wav(directory, samples, rate=8000, channels=1):
        path = Path(directory) / "synthetic.wav"
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))
        return path

    def test_silence(self):
        with tempfile.TemporaryDirectory() as d:
            rows, meta = analyzer.analyze(self.make_wav(d, [0] * 16000))
        self.assertEqual(len(rows), 2)
        self.assertEqual(meta["duration_s"], 2.0)
        self.assertEqual(meta["quiet_windows"], 2)
        self.assertEqual(meta["global_rms_dbfs"], float("-inf"))

    def test_known_sine_levels(self):
        values = [int(16384 * math.sin(2 * math.pi * 400 * i / 8000)) for i in range(8000)]
        with tempfile.TemporaryDirectory() as d:
            rows, meta = analyzer.analyze(self.make_wav(d, values), interval=0.5)
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(meta["global_sample_peak_dbfs"], -6.02, delta=0.1)
        self.assertAlmostEqual(meta["global_rms_dbfs"], -9.03, delta=0.1)

    def test_stereo_metadata(self):
        values = [v for pair in [(1000, -1000)] * 8000 for v in pair]
        with tempfile.TemporaryDirectory() as d:
            rows, meta = analyzer.analyze(self.make_wav(d, values, channels=2))
        self.assertEqual(meta["channels"], 2)
        self.assertEqual(len(rows), 1)
        self.assertEqual(meta["sample_rate_hz"], 8000)

    def test_quiet_then_loud(self):
        with tempfile.TemporaryDirectory() as d:
            rows, meta = analyzer.analyze(self.make_wav(d, [0] * 8000 + [8192] * 8000))
        self.assertTrue(rows[0]["quiet_window"])
        self.assertFalse(rows[1]["quiet_window"])
        self.assertAlmostEqual(rows[1]["rms_dbfs"], -12.04, delta=0.1)

    def test_level_jump(self):
        with tempfile.TemporaryDirectory() as d:
            rows, meta = analyzer.analyze(self.make_wav(d, [1000] * 8000 + [12000] * 8000))
        self.assertEqual(meta["level_jumps"], 1)
        self.assertGreater(rows[1]["level_jump_db"], 6)

    def test_csv_and_cli(self):
        with tempfile.TemporaryDirectory() as d:
            source = self.make_wav(d, [1000] * 8000)
            target = Path(d) / "report.csv"
            summary = Path(d) / "summary.txt"
            with contextlib.redirect_stdout(io.StringIO()):
                result = analyzer.main([str(source), "--csv", str(target), "--summary", str(summary)])
            self.assertEqual(result, 0)
            self.assertTrue(summary.exists())
            with target.open(encoding="utf-8-sig", newline="") as f:
                report = list(csv.DictReader(f))
            self.assertEqual(len(report), 1)
            self.assertIn("rms_dbfs", report[0])

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            analyzer.analyze(Path("/no/such/audio_fixture.mp3"))

    def test_invalid_interval(self):
        with tempfile.TemporaryDirectory() as d:
            source = self.make_wav(d, [0] * 10)
            with self.assertRaises(ValueError):
                analyzer.analyze(source, interval=0)


if __name__ == "__main__":
    unittest.main()
