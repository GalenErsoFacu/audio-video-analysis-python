"""Regression tests; recordings are generated locally, never sourced from customers."""
import contextlib
import csv
import io
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from music_transition_candidates import (
    decode_features, detect_candidates, features, main, percentile, write_csv,
)


class TransitionCandidateTests(unittest.TestCase):
    @staticmethod
    def wave_file(folder, samples, rate=8000, channels=1):
        path = Path(folder) / 'fixture.wav'
        with wave.open(str(path), 'wb') as target:
            target.setnchannels(channels)
            target.setsampwidth(2)
            target.setframerate(rate)
            target.writeframes(struct.pack(f'<{len(samples)}h', *samples))
        return path

    @staticmethod
    def tone(freq, duration=3, rate=8000, amp=12000):
        return [int(amp * math.sin(2 * math.pi * freq * i / rate))
                for i in range(round(duration * rate))]

    def test_percentile_and_empty(self):
        self.assertEqual(percentile([], 90), 0)
        self.assertEqual(percentile([10, 20, 30], 50), 20)
        self.assertEqual(percentile([10, 20, 30], 25), 15)

    def test_features_of_silence(self):
        row = features([0] * 2000)
        self.assertLessEqual(row['rms_dbfs'], -90)
        self.assertEqual(row['zcr'], 0)

    def test_bass_and_treble_differ(self):
        bass = features(self.tone(120, duration=0.5))
        treble = features(self.tone(1700, duration=0.5))
        self.assertGreater(bass['bass_ratio'], treble['bass_ratio'])
        self.assertGreater(treble['brightness_ratio'], bass['brightness_ratio'])

    def test_detect_synthetic_loudness_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, self.tone(440, 4, amp=1500) + self.tone(440, 4, amp=16000))
            windows, duration = decode_features(path, 0.5)
            result = detect_candidates(windows, min_gap=3, max_candidates=4)
        self.assertAlmostEqual(duration, 8.0, places=1)
        self.assertTrue(any(abs(row['time_s'] - 4.0) <= 1 for row in result), result)

    def test_detect_synthetic_timbre_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, self.tone(120, 4) + self.tone(1700, 4))
            windows, _ = decode_features(path, 0.5)
            result = detect_candidates(windows, min_gap=3, max_candidates=3)
        self.assertTrue(any(abs(row['time_s'] - 4.0) <= 1 for row in result), result)

    def test_constant_tone_has_no_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, self.tone(440, 6))
            windows, _ = decode_features(path)
            result = detect_candidates(windows)
        self.assertEqual(result, [])

    def test_silence_has_no_change(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, [0] * 8000 * 5)
            windows, _ = decode_features(path)
            result = detect_candidates(windows)
        self.assertEqual(result, [])

    def test_short_input(self):
        result = detect_candidates([{'time_s': 0}])
        self.assertEqual(result, [])

    def test_invalid_detection_settings(self):
        for settings in [dict(context=0), dict(min_gap=0), dict(max_candidates=0),
                         dict(sensitivity=-1), dict(sensitivity=101)]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                detect_candidates([], **settings)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            decode_features(Path('not_a_real_audio_file.mp3'))

    def test_invalid_window(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, [0] * 1000)
            with self.assertRaises(ValueError):
                decode_features(path, -0.25)

    def test_csv_format(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'candidates.csv'
            write_csv([{
                'time_s': 3.0, 'score': 0.5, 'rms_change_db': 3,
                'bass_balance_change': 0.1, 'brightness_change': 0.2,
                'zcr_change': 0.01, 'main_signal': 'level', 'status': 'Review by ear',
            }], output)
            with output.open(encoding='utf-8-sig', newline='') as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows[0]['status'], 'Review by ear')
            self.assertEqual(rows[0]['time_s'], '3.0')

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, self.tone(150, 4) + self.tone(1400, 4))
            target = Path(folder) / 'out.csv'
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                rc = main([str(path), '--csv', str(target)])
            self.assertEqual(rc, 0)
            self.assertTrue(target.exists())
            self.assertIn('Candidates must be listened to', stdout.getvalue())

    @unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
    def test_mp3_input(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.wave_file(folder, self.tone(400, 3))
            mp3 = Path(folder) / 'fixture.mp3'
            run = subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(path),
                                  '-codec:a', 'libmp3lame', str(mp3)], capture_output=True)
            if run.returncode:
                self.skipTest('MP3 encoder unavailable')
            windows, duration = decode_features(mp3)
            self.assertTrue(windows)
            self.assertAlmostEqual(duration, 3.0, delta=0.08)


if __name__ == '__main__':
    unittest.main()
