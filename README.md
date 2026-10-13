
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

