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

## Working tool: Music Annotation QA & CSV Export

**Source:** [`music_annotation_qa.py`](music_annotation_qa.py) · [Synthetic example JSON](examples/demo_music_sections.json) · [Example CSV output](examples/demo_music_sections.csv)

A second, tested Python tool for **quality checking manually prepared musical section annotations**. It helps review:

- Section order, durations, and timestamp overlaps
- Gaps in the annotated timeline (warnings)
- Missing instrument lists and repeated vibe tags (warnings)
- Invalid fields, timestamps, and nonpositive durations (errors)
- Instrument occurrence counts and export of validated sections to CSV

Supports section labels, start/end times, instruments, chord lists, key, vibe tags, and short notes.

**Run the demo:**

```bash
py music_annotation_qa.py examples/demo_music_sections.json --csv music_sections.csv
```

Expected summary:

```text
Sections checked: 4
Errors: 0 | Warnings: 0
Annotated duration: 68.000s
CSV saved: music_sections.csv
```

**Scope and limitations:** This is a validation/export tool for **annotations entered by a human**; it does **not automatically detect instruments, musical keys, chords, or boundaries from audio**. The demo data is original and synthetic, not from a client project.

**Automated tests:** [12 focused tests](tests/test_music_annotation_qa.py) exercise timestamp handling, overlap/gap detection, data validation, CSV generation, and the CLI. The existing GitHub Actions workflow runs these tests alongside the WAV analyzer tests.

## Working tool: Audio Timeline Dynamics (MP3/WAV)

**Source:** [`audio_timeline_analysis.py`](audio_timeline_analysis.py) · [8 synthetic tests](tests/test_audio_timeline_analysis.py)

A command-line analysis tool for **MP3, WAV, and other FFmpeg-readable audio**. Unlike the existing WAV inspector, this module measures how the sound level changes over time:

- RMS and decoded sample peak for consecutive time intervals
- Sample counts close to 0 dBFS
- Quiet intervals below an adjustable RMS threshold
- Large changes in RMS between adjacent intervals
- CSV export with timestamps for downstream review

**Requirements:** Python 3.10+, **FFmpeg and FFprobe on PATH**. The Python program itself uses only the standard library.

**Run on your own recording:**

```bash
py audio_timeline_analysis.py "my_recording.mp3" --interval 1 --csv audio_timeline.csv --summary audio_summary.txt
```

Both MP3 and WAV input work; the CSV and optional text summary are created locally. You can adjust `--silence-dbfs` and `--jump-db` for different material.

**Scope and limitations:** This measures the *decoded audio*; MP3 decoding can produce sample peaks above 0 dBFS, which alone does not prove that the original master clipped. Sample peak is not true peak and RMS is not LUFS. Detected level changes are **not verified musical section boundaries**, and the tool does not recognize instruments or harmony.

**Privacy:** The real recording used for development and its analysis report are **not published** in this repository. Automated tests use only synthetic audio generated in temporary directories.

## Automated checks

[![Python audio tests](https://github.com/GalenErsoFacu/audio-video-analysis-python/actions/workflows/python-tests.yml/badge.svg)](https://github.com/GalenErsoFacu/audio-video-analysis-python/actions/workflows/python-tests.yml)

The [regression test suite](tests/test_audio_quality_check.py) creates small synthetic WAV files and verifies PCM bit depths, mono/stereo metadata, dBFS calculations, silence, near-clipping, and missing-file errors.

Run the tests locally:

```bash
python -m unittest discover -s tests -v
```

The [GitHub Actions workflow](.github/workflows/python-tests.yml) runs these tests on Windows and Linux with multiple Python versions whenever changes are pushed or proposed. All test data is generated; no confidential audio is included.

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
