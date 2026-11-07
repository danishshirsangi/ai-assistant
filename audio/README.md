# Audio subsystem — planned for Version 0.2

The UI and reasoning layers are deliberately separated from audio capture.
The next milestone will add:

1. Push-to-talk global hotkey (press starts capture, release stops).
2. Microphone capture with `sounddevice`.
3. macOS system-audio capture through ScreenCaptureKit.
4. Local Whisper transcription.
5. Context refinement against recent conversation turns.
6. A consent/recording indicator and explicit stop/cancel controls.

Microphone and system audio should initially be stored as separate tracks so
the application can distinguish the user's speech from remote participants.
ScreenCaptureKit requires macOS screen & system audio recording permission.
Global shortcuts may require Accessibility/Input Monitoring permission.
Only record conversations when all applicable participants and workplace
policies permit it.
