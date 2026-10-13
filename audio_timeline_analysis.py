"""Analyze MP3/WAV dynamics over time with FFmpeg and the Python standard library.

Does not recognize instruments, chords, lyrics, or musical section boundaries.
Requires FFmpeg and FFprobe on PATH.

Usage:
    py audio_timeline_analysis.py "song.mp3" --csv audio_timeline.csv
"""
import argparse
from array import array
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


def dbfs(amplitude):
    return 20 * math.log10(amplitude) if amplitude > 0 else float("-inf")


def probe_audio(path):
    if shutil.which("ffprobe") is None:
        raise RuntimeError("ffprobe is required; install FFmpeg and add it to PATH")
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=sample_rate,channels,codec_name",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "ffprobe failed")
    try:
        stream = json.loads(completed.stdout)["streams"][0]
        return int(stream["sample_rate"]), int(stream["channels"]), stream["codec_name"]
    except (ValueError, IndexError, KeyError, TypeError) as error:
        raise RuntimeError("No valid audio stream was found") from error


def analyze(path, interval=1.0, silence_dbfs=-45.0, jump_db=6.0):
    """Analyze decoded audio in consecutive windows; return rows and metadata."""
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("interval must be a positive finite number")
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required; install FFmpeg and add it to PATH")
    rate, channels, codec = probe_audio(path)
    if rate <= 0 or channels <= 0:
        raise RuntimeError("Invalid audio stream properties")
    frames_per_window = max(1, round(rate * interval))
    samples_per_window = frames_per_window * channels
    bytes_per_window = 4 * samples_per_window
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(path), "-map", "0:a:0", "-vn",
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ar", str(rate), "-ac", str(channels), "pipe:1",
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rows = []
    pending = bytearray()
    total_frames = total_samples = 0
    total_energy = global_peak = 0.0
    try:
        while True:
            while len(pending) < bytes_per_window:
                chunk = process.stdout.read(bytes_per_window - len(pending))
                if not chunk:
                    break
                pending.extend(chunk)
            if not pending:
                break
            usable = len(pending) - len(pending) % (channels * 4)
            if usable == 0:
                raise RuntimeError("Decoder returned an incomplete audio frame")
            samples = array("f")
            samples.frombytes(pending[:usable])
            del pending[:usable]
            sample_count = len(samples)
            frames = sample_count // channels
            peak = energy = 0.0
            near_clipping = 0
            for sample in samples:
                amplitude = abs(sample)
                peak = max(peak, amplitude)
                energy += sample * sample
                near_clipping += amplitude >= 0.999
            rms = math.sqrt(energy / sample_count)
            start = total_frames / rate
            end = (total_frames + frames) / rate
            rows.append({
                "start_s": round(start, 3),
                "end_s": round(end, 3),
                "rms_dbfs": round(dbfs(rms), 2),
                "sample_peak_dbfs": round(dbfs(peak), 2),
                "near_clipping_samples": near_clipping,
                "quiet_window": rms <= 10 ** (silence_dbfs / 20),
                "level_jump_db": "",
            })
            total_frames += frames
            total_samples += sample_count
            total_energy += energy
            global_peak = max(global_peak, peak)
            if sample_count < samples_per_window:
                break
        error_output = process.stderr.read().decode("utf-8", errors="replace")
        if process.wait():
            raise RuntimeError(error_output.strip() or "Audio decoding failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    previous = None
    for row in rows:
        current = row["rms_dbfs"]
        if previous is not None and math.isfinite(current) and math.isfinite(previous):
            change = round(current - previous, 2)
            if abs(change) >= jump_db:
                row["level_jump_db"] = change
        previous = current
    metadata = {
        "file": path.name,
        "codec": codec,
        "sample_rate_hz": rate,
        "channels": channels,
        "duration_s": round(total_frames / rate, 3),
        "global_sample_peak_dbfs": round(dbfs(global_peak), 2),
        "global_rms_dbfs": round(dbfs(math.sqrt(total_energy / total_samples)), 2)
        if total_samples else float("-inf"),
        "window_seconds": interval,
        "silence_threshold_dbfs": silence_dbfs,
        "level_jump_threshold_db": jump_db,
        "quiet_windows": sum(row["quiet_window"] for row in rows),
        "level_jumps": sum(row["level_jump_db"] != "" for row in rows),
        "total_near_clipping_samples": sum(row["near_clipping_samples"] for row in rows),
    }
    return rows, metadata


def write_csv(rows, path):
    if not rows:
        raise ValueError("No decoded samples to export")
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def report(metadata, rows):
    return "\n".join([
        "AUDIO TIMELINE ANALYSIS",
        f'File: {metadata["file"]}',
        f'Codec: {metadata["codec"]}',
        f'Duration: {metadata["duration_s"]:.3f}s',
        f'Sample rate: {metadata["sample_rate_hz"]} Hz',
        f'Channels: {metadata["channels"]}',
        f'Global sample peak: {metadata["global_sample_peak_dbfs"]:.2f} dBFS',
        f'Global RMS: {metadata["global_rms_dbfs"]:.2f} dBFS',
        f'Windows: {len(rows)}',
        f'Quiet windows below {metadata["silence_threshold_dbfs"]} dBFS: {metadata["quiet_windows"]}',
        f'Adjacent level changes >= {metadata["level_jump_threshold_db"]} dB: {metadata["level_jumps"]}',
        f'Samples near clipping: {metadata["total_near_clipping_samples"]}',
        "",
        "Decoded sample peak is not true peak; RMS is not LUFS.",
        "Changes in level are not confirmed musical section boundaries.",
    ]) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Measure audio levels over time and export CSV")
    parser.add_argument("audio", type=Path, help="Input WAV, MP3, or another FFmpeg-readable audio file")
    parser.add_argument("--csv", type=Path, default=Path("audio_timeline.csv"))
    parser.add_argument("--summary", type=Path, help="Optional text summary")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--silence-dbfs", type=float, default=-45.0)
    parser.add_argument("--jump-db", type=float, default=6.0)
    args = parser.parse_args(argv)
    try:
        rows, metadata = analyze(args.audio, args.interval, args.silence_dbfs, args.jump_db)
        write_csv(rows, args.csv)
        output = report(metadata, rows)
        if args.summary:
            args.summary.write_text(output, encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(output)
    print(f"CSV saved: {args.csv}")
    if args.summary:
        print(f"Summary saved: {args.summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
