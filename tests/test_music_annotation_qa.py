"""Tests for the manual music annotation QA helper."""
import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from music_annotation_qa import analyze, main, save_csv, seconds


class MusicAnnotationQATests(unittest.TestCase):
    @staticmethod
    def section(label='Intro', start='00:00', end='00:10', **other):
        return {'label': label, 'start': start, 'end': end, 'instruments': ['Bass'], **other}

    def test_time_parsing(self):
        self.assertEqual(seconds('01:02.5'), 62.5)
        self.assertEqual(seconds('01:01:02'), 3662)
        self.assertEqual(seconds(3.5), 3.5)

    def test_invalid_time_formats(self):
        for bad in ['00:62', '-1', True, float('nan'), 'ab:11', None]:
            with self.subTest(timestamp=bad), self.assertRaises(ValueError):
                seconds(bad)

    def test_clean_annotations(self):
        rows, errors, warnings = analyze({'sections': [
            self.section(end='00:10'),
            self.section('Verse', '00:10', '00:22', chords=['Am', 'F'], vibe_tags=['Warm'])
        ]})
        self.assertEqual(len(rows), 2)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(rows[1]['chords'], 'Am | F')

    def test_overlap_error(self):
        _, errors, _ = analyze({'sections': [self.section(), self.section('Verse', '00:09', '00:20')]})
        self.assertTrue(any('overlaps' in error for error in errors))

    def test_gap_warning(self):
        _, errors, warnings = analyze({'sections': [self.section(), self.section('Verse', '00:12', '00:20')]})
        self.assertFalse(errors)
        self.assertTrue(any('gap' in warning for warning in warnings))

    def test_empty_or_invalid_document(self):
        for doc in [{}, {'sections': []}, {'sections': 'invalid'}]:
            self.assertTrue(analyze(doc)[1])

    def test_missing_instruments_and_duplicate_tags(self):
        rows, errors, warnings = analyze({'sections': [
            {'label': 'Intro', 'start': 0, 'end': 10, 'vibe_tags': ['Warm', 'warm']}
        ]})
        self.assertFalse(errors)
        self.assertEqual(len(warnings), 2)
        self.assertEqual(len(rows), 1)

    def test_invalid_field_type(self):
        _, errors, _ = analyze({'sections': [self.section(instruments=['Bass', 17])]})
        self.assertTrue(errors)
        _, errors, _ = analyze({'sections': [self.section(notes=12)]})
        self.assertTrue(errors)

    def test_zero_duration_error(self):
        _, errors, _ = analyze({'sections': [self.section(end='00:00')]})
        self.assertTrue(errors)

    def test_csv_export(self):
        rows, errors, _ = analyze({'sections': [self.section(notes='Bright, with drums')]})
        self.assertFalse(errors)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'data.csv'
            save_csv(rows, path)
            with path.open(encoding='utf-8-sig', newline='') as stream:
                saved = list(csv.DictReader(stream))
        self.assertEqual(saved[0]['notes'], 'Bright, with drums')

    def test_cli_demo_end_to_end(self):
        demo = Path(__file__).resolve().parents[1] / 'examples/demo_music_sections.json'
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'report.csv'
            with contextlib.redirect_stdout(io.StringIO()) as log:
                code = main([str(demo), '--csv', str(dest)])
            self.assertEqual(code, 0)
            self.assertTrue(dest.exists())
            self.assertIn('Sections checked: 4', log.getvalue())

    def test_cli_rejects_invalid_data_without_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            input_path = Path(temp) / 'bad.json'
            output_path = Path(temp) / 'report.csv'
            input_path.write_text(json.dumps({'sections': [self.section(end='00:00')]}))
            with contextlib.redirect_stdout(io.StringIO()):
                code = main([str(input_path), '--csv', str(output_path)])
            self.assertEqual(code, 1)
            self.assertFalse(output_path.exists())


if __name__ == '__main__':
    unittest.main()
