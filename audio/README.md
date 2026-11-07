# Audio subsystem — Version 0.2

## Included
- Global push-to-talk using Control (press to start, release to stop).
- In-app Start/Stop fallback.
- Microphone capture via sounddevice, saved as WAV.
- Microphone selector for macOS default, OnePlus Buds, MacBook built-in mic, or other available input devices.
- Refresh button to rescan devices after connecting or disconnecting a headset; input selection is locked during recording.
- System audio via Apple's ScreenCaptureKit Swift helper, saved as M4A.
- Local transcription via MLX Whisper on Apple Silicon.
- Separate microphone / system-audio labels.
- Local Ollama transcript cleanup preserving meaningful technical and conversational context.
- Interview answer generation in the main app and floating overlay.

## Setup
Install Xcode Command Line Tools:

```bash
xcode-select --install
```

Install audio dependencies from the project root:

```bash
pip install -r requirements-audio-macos.txt
```

The Swift helper is compiled automatically on first recording. Whisper model files
are downloaded once on first transcription; inference then runs locally.

## macOS permissions
- Microphone: allow the Python app.
- Screen & System Audio Recording: allow the terminal/Python app.
- Accessibility / Input Monitoring: allow the app for the global Control shortcut.

Restart after changing permissions. If the global shortcut is blocked, use the
visible Start/Stop button.

## Privacy
Audio is stored in `data/audio_sessions/`, which is ignored by Git. Do not record
without appropriate participant consent and workplace authorization.

## Current limits
Transcription begins after recording stops; there are no live streaming captions yet.
English is the default language. System audio requires macOS 13+.
