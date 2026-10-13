"""Validate manually prepared music section annotations and export a CSV report.

This tool validates metadata. It does NOT listen to audio, infer chords, identify
instruments, or produce automated musical annotations.

Example:
    python music_annotation_qa.py examples/demo_music_sections.json --csv sections.csv
"""

import argparse
import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path


def seconds(value):
    """Parse numeric seconds, MM:SS, or HH:MM:SS timestamps."""
    if isinstance(value, bool):
        raise ValueError('boolean is not a timestamp')
    if isinstance(value, (int, float)):
        if not math.isfinite(value) or value < 0:
            raise ValueError('timestamp must be a nonnegative finite number')
        return float(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('timestamp must be a number or time string')
    value = value.strip()
    parts = value.split(':')
    try:
        if len(parts) == 1:
            result = float(parts[0])
        elif len(parts) == 2:
            minutes, sec = int(parts[0]), float(parts[1])
            if minutes < 0 or not (0 <= sec < 60):
                raise ValueError('minutes/seconds out of range')
            result = minutes * 60 + sec
        elif len(parts) == 3:
            hours, minutes, sec = int(parts[0]), int(parts[1]), float(parts[2])
            if hours < 0 or not (0 <= minutes < 60) or not (0 <= sec < 60):
                raise ValueError('hours/minutes/seconds out of range')
            result = hours * 3600 + minutes * 60 + sec
        else:
            raise ValueError('use seconds, MM:SS, or HH:MM:SS')
    except (ValueError, OverflowError) as exc:
        raise ValueError(f'invalid timestamp {value!r}') from exc
    if not math.isfinite(result) or result < 0:
        raise ValueError('timestamp must be a nonnegative finite number')
    return result


def string_list(value, field):
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f'{field} must be a list of nonempty strings')
    return [item.strip() for item in value]


def analyze(document):
    """Return (rows, errors, warnings) from a JSON document."""
    if not isinstance(document, dict) or not isinstance(document.get('sections'), list):
        return [], ['Root must be an object containing a sections list'], []
    if not document['sections']:
        return [], ['At least one section is required'], []

    rows, errors, warnings = [], [], []
    previous_end = None
    for index, section in enumerate(document['sections'], 1):
        prefix = f'Section {index}'
        if not isinstance(section, dict):
            errors.append(f'{prefix}: must be an object')
            continue
        label = section.get('label')
        if not isinstance(label, str) or not label.strip():
            errors.append(f'{prefix}: label must be nonempty text')
            continue
        try:
            start = seconds(section.get('start'))
            end = seconds(section.get('end'))
            instruments = string_list(section.get('instruments'), 'instruments')
            vibes = string_list(section.get('vibe_tags'), 'vibe_tags')
            chords = string_list(section.get('chords'), 'chords')
        except ValueError as exc:
            errors.append(f'{prefix} ({label}): {exc}')
            continue
        if end <= start:
            errors.append(f'{prefix} ({label}): end must be greater than start')
            continue
        if previous_end is not None:
            if start < previous_end - 1e-6:
                errors.append(f'{prefix} ({label}): overlaps the previous section by {previous_end - start:.3f}s')
            elif start > previous_end + 1e-6:
                warnings.append(f'{prefix} ({label}): {start - previous_end:.3f}s gap before this section')
        if index == 1 and start > 1e-6:
            warnings.append(f'{prefix} ({label}): timeline starts at {start:.3f}s, not zero')
        if not instruments:
            warnings.append(f'{prefix} ({label}): no instruments listed')
        if len({tag.casefold() for tag in vibes}) != len(vibes):
            warnings.append(f'{prefix} ({label}): repeated vibe tag')
        previous_end = end
        key = section.get('key', '')
        notes = section.get('notes', '')
        if not isinstance(key, str) or not isinstance(notes, str):
            errors.append(f'{prefix} ({label}): key and notes must be strings')
            continue
        rows.append({
            'section': index,
            'label': label.strip(),
            'start_s': f'{start:.3f}',
            'end_s': f'{end:.3f}',
            'duration_s': f'{end - start:.3f}',
            'key': key.strip(),
            'chords': ' | '.join(chords),
            'instruments': ' | '.join(instruments),
            'vibe_tags': ' | '.join(vibes),
            'notes': notes.strip(),
        })
    return rows, errors, warnings


def save_csv(rows, target):
    with Path(target).open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Music section annotation QA (manual metadata, not audio recognition)')
    parser.add_argument('input', type=Path, help='JSON file containing sections')
    parser.add_argument('--csv', type=Path, help='Optional CSV output path')
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding='utf-8') as stream:
            document = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f'ERROR: Cannot read input JSON: {exc}', file=sys.stderr)
        return 2

    rows, errors, warnings = analyze(document)
    for issue in errors:
        print(f'ERROR: {issue}')
    for issue in warnings:
        print(f'WARNING: {issue}')
    print(f'Sections checked: {len(document["sections"]) if isinstance(document, dict) and isinstance(document.get("sections"), list) else 0}')
    print(f'Errors: {len(errors)} | Warnings: {len(warnings)}')
    if errors:
        print('CSV not written because validation failed.')
        return 1

    count = Counter()
    for section in document['sections']:
        count.update(set(item.casefold() for item in section.get('instruments', [])))
    if count:
        print('Instruments by section: ' + ', '.join(f'{name} ({qty})' for name, qty in sorted(count.items())))
    print(f'Annotated duration: {sum(float(row["duration_s"]) for row in rows):.3f}s')
    if args.csv:
        try:
            save_csv(rows, args.csv)
        except OSError as exc:
            print(f'ERROR: Could not write CSV: {exc}', file=sys.stderr)
            return 2
        print(f'CSV saved: {args.csv}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
