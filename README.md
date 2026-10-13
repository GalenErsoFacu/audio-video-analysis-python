
# Audio & Video Analysis with Python

## About Me
I'm a professional Audio Engineer, Music Producer, and Musician with over 25 years of experience in audio production, mixing, mastering, and critical listening.

I also have experience in AI audio/video annotation, transcription evaluation, and quality assurance.

## Project Overview
This repository documents my practical exploration of Python-based audio and video analysis.

## Technologies
- Python
- OpenAI Whisper
- FFmpeg
- OpenCV
- PySceneDetect

## Project Goals
- Audio transcription and timestamp analysis
- Video scene and camera-cut detection
- Audiovisual content analysis
- Audio quality evaluation
- Automated annotation workflows

## Current Status
Work in progress. Demonstration scripts and documentation will be added as they are developed and tested.

## Professional Profile
[LinkedIn](https://www.linkedin.com/in/facusayago)


## Audio Quality Analysis Tool

A Python utility for analyzing uncompressed PCM WAV files.

### Features
- Audio duration and sample rate
- Channel count and bit depth
- Peak amplitude in dBFS
- RMS level in dBFS
- Near-clipping sample detection
- Supports 8, 16, 24, and 32-bit PCM WAV

### Usage

Run the following command:

```bash
python audio_quality_check.py example.wav
```

### Validation

The script was tested with a 2-second, 440 Hz WAV file at 44.1 kHz and 16-bit resolution.

Results:
- Peak: -12.04 dBFS
- RMS: -15.05 dBFS
- Near-clipping samples: 0

No external Python libraries are required.


## Audio Quality Analysis Tool

A Python-based tool for technical audio inspection and quality assessment.

### Features
- WAV file analysis
- Duration and sample rate detection
- Channel count and bit depth
- Peak level measurement (dBFS)
- RMS level measurement (dBFS)
- Near-clipping sample detection
- Support for uncompressed PCM WAV files

### How to Run

Requirements:
- Python 3.10 or newer
- No external libraries required

Command:

    python audio_quality_check.py example.wav

Replace example.wav with the name of your WAV file.

### Test Results

Successfully tested with a 2-second, 440 Hz WAV test signal.

- Sample rate: 44,100 Hz
- Bit depth: 16-bit
- Channels: Mono
- Peak level: -12.04 dBFS
- RMS level: -15.05 dBFS
- Near-clipping samples: 0

### Applications

- Audio Quality Assurance
- AI Audio Dataset Evaluation
- Technical Audio Inspection
- Audio Annotation Workflows
- Digital Audio Analysis

### Development Status

Initial audio analysis module implemented and locally tested.
Further audiovisual analysis features are planned.


