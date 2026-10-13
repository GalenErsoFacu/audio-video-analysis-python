# Audio Analysis & AI Tools

**Python Audio Processing · Audio Quality Assurance · AI Annotation**

I'm **Facundo Sayago**, an audio professional, musician, and music producer based in Argentina, with over 25 years of practical experience in live sound, recording, mixing, mastering, and critical listening. I also work on audio/video annotation and quality review for AI projects.

This repository documents hands-on, reproducible Python tools. It distinguishes **working code** from planned experiments.

## Working tool: WAV Audio Quality Analyzer

**Source:** [`audio_quality_check.py`](audio_quality_check.py)

A command-line tool that inspects **uncompressed integer PCM WAV** files.

It reports:
- Duration, sample rate, and channel count
- Sample bit depth (8-, 16-, 24-, or 32-bit integer PCM)
- Sample peak in dBFS
- Overall RMS in dBFS
- Number of samples at or above a near-clipping threshold

**Requirements:** Python 3.10+; no third-party packages.

### Run

```bash
py audio_quality_check.py example.wav
```

Replace `example.wav` with your own WAV file path. On systems where `py` is unavailable, use `python`.

**Scope:** The script does not currently support floating-point WAV, compressed formats, LUFS measurement, or true-peak detection. Its RMS measurement is a sample-based measurement across all channels.

### Local validation

Tested with a generated 2-second, 440 Hz mono PCM WAV file (44,100 Hz, 16-bit).

| Measurement | Observed result |
|---|---|
| Duration | 2.00 s |
| Sample rate | 44,100 Hz |
| Channels | Mono |
| Bit depth | 16-bit |
| Sample peak | -12.04 dBFS |
| RMS | -15.05 dBFS |
| Near-clipping samples | 0 |

## Professional focus

- Music annotation: instrumentation, musical structure, harmony, and listening-based analysis
- Audio transcription quality review, timestamp checking, and speaker labeling
- Sound recording, editing, mixing, and mastering
- AI-assisted audio/video workflows

## Tools being explored

Python, OpenAI Whisper, FFmpeg, OpenCV, and PySceneDetect.

**Planned work — not yet published as working modules:** timestamped transcription, subtitle generation, and video scene-cut detection.

## Contact

[LinkedIn](https://www.linkedin.com/in/facusayago) · [GitHub](https://github.com/GalenErsoFacu)

> Only self-created demonstration data and non-confidential code belong in this public repository.
