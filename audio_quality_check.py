import wave
import math
import sys

def analyze_audio(filename):
    with wave.open(filename, "rb") as audio:
        channels = audio.getnchannels()
        sample_rate = audio.getframerate()
        frames = audio.getnframes()
        width = audio.getsampwidth()

        if width not in (1, 2, 3, 4):
            raise ValueError("Unsupported PCM bit depth")

        peak = 0.0
        energy = 0.0
        clipped = 0
        count = 0

        while True:
            data = audio.readframes(4096)
            if not data:
                break

            for i in range(0, len(data), width):
                sample = data[i:i + width]

                if width == 1:
                    value = (sample[0] - 128) / 128
                else:
                    value = int.from_bytes(
                        sample, "little", signed=True
                    ) / (2 ** (width * 8 - 1))

                level = abs(value)
                peak = max(peak, level)
                energy += value * value
                clipped += level >= 0.999
                count += 1

        rms = math.sqrt(energy / count) if count else 0

        def dbfs(value):
            return 20 * math.log10(value) if value > 0 else float("-inf")

        print("=== AUDIO QUALITY REPORT ===")
        print(f"Duration: {frames / sample_rate:.2f} seconds")
        print(f"Sample rate: {sample_rate} Hz")
        print(f"Channels:
