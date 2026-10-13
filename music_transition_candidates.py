"""Find candidate acoustic transitions in an audio recording for human review.

Uses FFmpeg and only the Python standard library. This is NOT automatic
verse/chorus recognition, instrument detection, or musical transcription.

Usage:
    py music_transition_candidates.py "song.mp3" --csv candidates.csv
"""

import argparse
from array import array
import csv
import math
from pathlib import Path
import shutil
import subprocess
import sys

SAMPLE_RATE = 8000


def percentile(values, pct):
    if not values:
        return 0.0
    data = sorted(values)
    position = (len(data) - 1) * pct / 100
    low = int(position)
    high = min(low + 1, len(data) - 1)
    return data[low] + (data[high] - data[low]) * (position - low)


def features(samples, sample_rate=SAMPLE_RATE):
    """Compute proxies for level, bass content, brightness, and zero crossings.

    These are time-domain summaries, not spectral FFT bins.
    """
    if not samples:
        return None
    lp_bass = lp_treble = 0.0
    a_bass = 1 - math.exp(-2 * math.pi * 180 / sample_rate)
    a_treble = 1 - math.exp(-2 * math.pi * 1250 / sample_rate)
    energy = bass_energy = high_energy = 0.0
    crossing = 0
    previous = 0.0
    for i, sample in enumerate(samples):
        x = sample / 32768.0
        lp_bass += a_bass * (x - lp_bass)
        lp_treble += a_treble * (x - lp_treble)
        energy += x * x
        bass_energy += lp_bass * lp_bass
        high_energy += (x - lp_treble) ** 2
        if i and ((x >= 0) != (previous >= 0)):
            crossing += 1
        previous = x
    n = len(samples)
    rms = math.sqrt(energy / n)
    denom = energy if energy > 1e-10 else 1e-10
    return {
        'rms_dbfs': max(-100.0, 20 * math.log10(max(rms, 1e-5))),
        'bass_ratio': min(1.5, math.sqrt(bass_energy / denom)),
        'brightness_ratio': min(1.5, math.sqrt(high_energy / denom)),
        'zcr': crossing / n,
    }


def decode_features(path, window_seconds=0.5):
    """Decode audio in streaming windows without retaining samples in memory."""
    if not path.is_file():
        raise FileNotFoundError(f'No such audio file: {path}')
    if not shutil.which('ffmpeg'):
        raise RuntimeError('FFmpeg is not on PATH')
    if not math.isfinite(window_seconds) or window_seconds <= 0:
        raise ValueError('window_seconds must be a positive finite number')
    count = max(1, round(window_seconds * SAMPLE_RATE))
    size = count * 2
    command = [
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-i', str(path), '-map', '0:a:0', '-vn', '-ac', '1',
        '-ar', str(SAMPLE_RATE), '-f', 's16le', '-acodec', 'pcm_s16le', 'pipe:1',
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rows = []
    decoded_frames = 0
    try:
        while True:
            buf = bytearray()
            while len(buf) < size:
                chunk = process.stdout.read(size - len(buf))
                if not chunk:
                    break
                buf.extend(chunk)
            if not buf:
                break
            if len(buf) % 2:
                raise RuntimeError('Incomplete PCM sample from FFmpeg')
            samples = array('h')
            samples.frombytes(buf)
            if sys.byteorder != 'little':
                samples.byteswap()
            row = features(samples)
            row['time_s'] = decoded_frames / SAMPLE_RATE
            rows.append(row)
            decoded_frames += len(samples)
            if len(buf) < size:
                break
        stderr = process.stderr.read().decode('utf-8', errors='replace')
        if process.wait():
            raise RuntimeError(f'Audio decoder error: {stderr.strip()}')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    return rows, decoded_frames / SAMPLE_RATE


def mean_features(items):
    keys = ('rms_dbfs', 'bass_ratio', 'brightness_ratio', 'zcr')
    return {key: sum(row[key] for row in items) / len(items) for key in keys}


def detect_candidates(windows, context=3, min_gap=9.0, max_candidates=12, sensitivity=85):
    """Compare adjacent groups of windows; emit review candidates, not section labels."""
    if context < 1 or min_gap <= 0 or max_candidates < 1 or not 0 <= sensitivity <= 100:
        raise ValueError('invalid detection settings')
    if len(windows) < 2 * context + 1:
        return []
    scored = []
    for i in range(context, len(windows) - context):
        before = mean_features(windows[i - context:i])
        after = mean_features(windows[i:i + context])
        d_level = after['rms_dbfs'] - before['rms_dbfs']
        d_bass = after['bass_ratio'] - before['bass_ratio']
        d_bright = after['brightness_ratio'] - before['brightness_ratio']
        d_zcr = after['zcr'] - before['zcr']
        factors = {
            'level': min(abs(d_level) / 12, 2),
            'bass_balance': min(abs(d_bass) / 0.22, 2),
            'brightness': min(abs(d_bright) / 0.17, 2),
            'zero_crossings': min(abs(d_zcr) / 0.09, 2),
        }
        score = 0.42 * factors['level'] + 0.22 * factors['bass_balance'] + 0.25 * factors['brightness'] + 0.11 * factors['zero_crossings']
        scored.append({
            'time_s': round(windows[i]['time_s'], 2),
            'score': round(score, 4),
            'rms_change_db': round(d_level, 2),
            'bass_balance_change': round(d_bass, 4),
            'brightness_change': round(d_bright, 4),
            'zcr_change': round(d_zcr, 4),
            'main_signal': max(factors, key=factors.get),
            'status': 'Review by ear',
        })
    threshold = max(0.27, percentile([row['score'] for row in scored], sensitivity))
    # Strongest first, then keep events separated by at least min_gap seconds.
    strongest = sorted((r for r in scored if r['score'] >= threshold), key=lambda r: (-r['score'], r['time_s']))
    selected = []
    for row in strongest:
        if all(abs(row['time_s'] - picked['time_s']) >= min_gap for picked in selected):
            selected.append(row)
        if len(selected) == max_candidates:
            break
    return sorted(selected, key=lambda r: r['time_s'])


def write_csv(rows, path):
    fields = ('time_s', 'score', 'rms_change_db', 'bass_balance_change',
              'brightness_change', 'zcr_change', 'main_signal', 'status')
    with Path(path).open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate acoustic transition candidates for manual musical review')
    parser.add_argument('audio', type=Path, help='MP3/WAV or other FFmpeg-readable audio file')
    parser.add_argument('--csv', type=Path, default=Path('music_transition_candidates.csv'))
    parser.add_argument('--window', type=float, default=0.5, help='Analysis window in seconds (default 0.5)')
    parser.add_argument('--min-gap', type=float, default=9.0, help='Minimum distance between candidates in seconds')
    parser.add_argument('--max-candidates', type=int, default=12)
    parser.add_argument('--sensitivity', type=float, default=85.0, help='Score percentile, 0..100; lower is more sensitive')
    args = parser.parse_args(argv)
    try:
        if not math.isfinite(args.min_gap) or args.min_gap <= 0:
            raise ValueError('--min-gap must be positive')
        windows, duration = decode_features(args.audio, args.window)
        results = detect_candidates(windows, min_gap=args.min_gap,
                                    max_candidates=args.max_candidates, sensitivity=args.sensitivity)
        write_csv(results, args.csv)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print(f'Audio: {args.audio.name}')
    print(f'Duration: {duration:.2f}s | Analyzed windows: {len(windows)}')
    print(f'Acoustic change candidates: {len(results)}')
    for r in results:
        minutes, second = divmod(r['time_s'], 60)
        print(f'  {int(minutes):02d}:{second:05.2f}   novelty={r["score"]:.2f}   primary={r["main_signal"]}')
    print(f'CSV saved: {args.csv}')
    print('Candidates must be listened to and validated; they are NOT confirmed song sections.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
