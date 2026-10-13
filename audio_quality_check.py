"""Simple PCM WAV audio quality report.

Usage:
    py audio_quality_check.py path/to/audio.wav

Supports uncompressed integer PCM WAV files with 8, 16, 24, or 32-bit samples.
"""

import argparse
import math
import sys
import wave
from pathlib import Path


def dbfs(amplitude: float) -> float:
    """Convert a normalized linear amplitude to dBFS."""
    return 20 * math.log10(amplitude) if amplitude > 0 else float("-inf")


def analyze_audio(filename: Path) -> None:
    with wave.open(str(filename), "rb") as audio:
        if audio.getcomptype() != "NONE":
            raise ValueError("Only uncompressed PCM WAV files are supported")

        channels = audio.getnchannels()
        sample_rate = audio.getframerate()
        frames = audio.getnframes()
        sample_width = audio.getsampwidth()

        if sample_width not in (1, 2, 3, 4):
            raise ValueError("Unsupported PCM bit depth")
        if sample_rate <= 0 or channels <= 0:
            raise ValueError("Invalid WAV metadata")

        peak = 0.0
        energy = 0.0
        near_clipping_samples = 0
        sample_count = 0
        denominator = float(1 << (sample_width * 8 - 1))

        while True:
            chunk = audio.readframes(4096)
            if not chunk:
                break

            for offset in range(0, len(chunk), sample_width):
                sample_bytes = chunk[offset:offset + sample_width]
                if len(sample_bytes) != sample_width:
                    raise ValueError("Incomplete PCM sample in WAV file")

                if sample_width == 1:
                    # Unsigned 8-bit PCM WAV is centered at 128.
                    sample_value = sample_bytes[0] - 128
                else:
                    sample_value = int.from_bytes(
                        sample_bytes, byteorder="little", signed=True
                    )

                level = abs(sample_value / denominator)
                peak = max(peak, level)
                energy += level * level
                near_clipping_samples += level >= 0.999
                sample_count += 1

    rms = math.sqrt(energy / sample_count) if sample_count else 0.0
    print("=== AUDIO QUALITY REPORT ===")
    print(f"File: {filename.name}")
    print(f"Duration: {frames / sample_rate:.2f} seconds")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Channels: {channels}")
    print(f"Bit depth: {sample_width * 8} bit")
    print(f"Peak level: {dbfs(peak):.2f} dBFS")
    print(f"RMS level: {dbfs(rms):.2f} dBFS")
    print(f"Samples near clipping: {near_clipping_samples}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze uncompressed PCM WAV audio")
    parser.add_argument("file", type=Path, help="Path to a .wav file")
    args = parser.parse_args()

    try:
        analyze_audio(args.file)
    except (OSError, ValueError, wave.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
