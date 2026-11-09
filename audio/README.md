# Audio subsystem

The audio subsystem captures the user's microphone and Mac system audio and transcribes both tracks locally. In this Gemini experiment, the resulting transcript is then sent to Gemini for answer generation.

## Controls

- **Control + Option + R press:** start recording.
- **Control + Option + R press again:** stop recording and begin transcription.
- **Control + Option + H:** hide the AI Meeting Assistant main window; press again to restore it.
- Hiding the window does not stop recording, transcription or answer generation.
- Holding either shortcut is not required.
- The in-app Start/Stop and Hide window buttons are fallbacks.
- The microphone dropdown selects the input device; Refresh rescans devices. Device selection is locked during recording.

## Components

| Component | Responsibility |
|---|---|
| `controller.py` | Control + Option + R recording toggle, Control + Option + H window visibility toggle, microphone capture and cleanup |
| `macos_system_audio.swift` | ScreenCaptureKit system audio capture and AVFoundation M4A writer |
| `transcriber.py` | MLX Whisper local transcription |

## Install

From the repository root with the Python 3.12 virtual environment active:

```bash
xcode-select --install
python -m pip install -r requirements-audio-macos.txt
```

The app compiles the Swift helper automatically on the first recording. MLX Whisper downloads its model on first transcription.

### Dependencies

- `sounddevice`: microphone capture via PortAudio.
- `soundfile`: temporary WAV output for microphone audio.
- `numpy`: audio frame buffering/concatenation.
- `pynput`: global Control + Option + R and Control + Option + H keyboard shortcuts.
- `mlx-whisper`: local Apple Silicon Whisper inference.
- `pyobjc-framework-Cocoa`: macOS capture-privacy window API.
- Xcode Command Line Tools: `swiftc` compiler and macOS SDK for the ScreenCaptureKit helper.

**FFmpeg is optional, not an app dependency.** The current app writes WAV using SoundFile and M4A using AVFoundation; Whisper reads these files directly. Install FFmpeg only for manual conversion or audio diagnostics: `brew install ffmpeg`.

## Capture and transcription lifecycle

1. Control + Option + R starts a new unique temporary session.
2. Microphone frames are buffered by sounddevice.
3. ScreenCaptureKit writes system audio to M4A.
4. The second Control + Option + R press stops capture and finalizes both tracks.
5. MLX Whisper transcribes each track locally.
6. The transcript is passed to the Gemini-backed answer workflow; transcript text and recent conversation context leave the Mac for cloud inference.
7. The temporary session directory is removed in a `finally` block, even if transcription fails.
8. A new Control + Option + R press creates a separate fresh session.

Audio is temporarily written under the operating system's temp directory; it is not retained in the repository's `data/` directory. Startup cleanup attempts to remove stale folders belonging to processes that are no longer running.

## Permissions

Grant the launching app (Terminal, VS Code, etc.):

- Microphone
- Screen & System Audio Recording
- Accessibility / Input Monitoring for the global Control + Option + R and Control + Option + H shortcuts

Restart the launching app after changing permissions. macOS permission labels vary by version.

## Troubleshooting

- **Global shortcuts unavailable:** grant Accessibility/Input Monitoring or use the in-app buttons.
- **Control + Option + H unavailable:** confirm the app's global keyboard listener started; use the Hide window button while the window is visible.
- **Control + Option + R unavailable:** use the in-app recording button.
- **Mic unavailable:** grant Microphone access and select/refresh the correct input device.
- **System audio unavailable:** macOS 13+, Screen & System Audio Recording permission and Xcode Command Line Tools are required.
- **Native segmentation fault:** use a clean Python 3.12 environment and reinstall both requirements files; native packages may crash without a Python traceback.
- **Whisper first run:** model download requires internet; later inference runs locally.

## Privacy

Only record with required participant consent and workplace authorization. Audio capture and Whisper transcription remain local, but the recognized transcript is sent to Gemini to generate answers. Resume text is also sent to Gemini for embeddings. Free-tier Gemini API content may be used by Google to improve its products; do not use confidential meetings or unredacted personal resumes without reviewing the applicable terms. The Generate Content API request is not stored as an Interactions record, but that does not make requests local or override free-tier data-use terms. Temporary-file cleanup is not secure erasure and should not be treated as a guarantee against forensic recovery.
