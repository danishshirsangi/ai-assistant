# Interview Copilot

A local-first macOS desktop copilot for meeting and interview assistance. It captures your microphone and Mac system audio, transcribes both tracks locally with MLX Whisper, and streams generated responses directly into a single always-on-top main window.

> **Privacy note:** Only record meetings when participant consent, company policy and applicable law permit it. The capture-privacy window setting is a best-effort macOS API hint, not a guarantee that every meeting or screen-sharing application will hide the windows.

## Features

- Native desktop UI built with Python and PySide6.
- Local LLM and embeddings through Ollama.
- Resume/document indexing with SQLite-backed retrieval.
- Microphone capture with selectable input device.
- macOS system-audio capture through Apple's ScreenCaptureKit.
- Local transcription with MLX Whisper on Apple Silicon.
- **Toggle hotkey:** press **Control + Option + R** once to start recording; press it again to stop. No key-holding required.
- Live token-by-token answers appear in the main window for both typed questions and interview transcripts.
- Visible Start/Stop button as a fallback.
- Transcript labels distinguish microphone audio from other participants/system audio.
- Local transcript refinement and answer generation.
- Single main application window with an always-on-top setting and a dedicated live answer pane.
- Adaptive business-case and executive/managerial response frameworks.
- macOS accessory-app mode (no Dock icon or normal Cmd-Tab entry).
- Capture privacy toggle requests exclusion of the main window from compatible macOS capture APIs; this is best-effort and does not guarantee invisibility in screen sharing.

## Supported environment

Recommended setup:

- macOS 13 or newer (ScreenCaptureKit system-audio capture).
- Apple Silicon Mac (MLX Whisper acceleration).
- **Python 3.12** recommended for the current native dependency stack. Avoid using a very new Python release until PySide6, MLX and audio wheels are confirmed compatible.
- Xcode Command Line Tools.
- Ollama installed and running locally.

Python 3.12 is recommended because MLX and other compiled dependencies are tied to supported Python/macOS/architecture combinations. The app may install on other versions, but installation success does not guarantee native runtime stability.

## 1. Install system tools

Install Homebrew if it is not already installed: https://brew.sh/

Install Python 3.12 and Xcode Command Line Tools:

```bash
brew install python@3.12
xcode-select --install
```

Install Ollama: https://ollama.com/download

Download the default models:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Start the Ollama service if it is not already running:

```bash
ollama serve
```

## 2. Clone and install Python dependencies

```bash
git clone https://github.com/danishshirsangi/ai-assistant.git
cd ai-assistant
git switch feature/single-window-live-responses
```

Create and activate a Python 3.12 virtual environment:

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
python --version
```

Install the core app and optional macOS audio dependencies:

```bash
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt
python -m pip install -r requirements-audio-macos.txt
```

The audio requirements include:

| Package | Purpose |
|---|---|
| `sounddevice` | Microphone input capture through PortAudio |
| `soundfile` | Write microphone PCM audio to temporary WAV |
| `numpy` | Buffer and combine microphone audio frames |
| `pynput` | Global Control + Option + R keyboard shortcut |
| `mlx-whisper` | Local Whisper transcription on Apple Silicon |
| `pyobjc-framework-Cocoa` | macOS window capture privacy API |
| `PySide6` | Desktop UI and Qt event loop |
| `requests` | Local Ollama HTTP API |
| `PyMuPDF` | PDF text extraction |
| `python-docx` | DOCX text extraction |

The ScreenCaptureKit helper is written in Swift and compiled automatically with `swiftc` the first time audio capture starts. Xcode Command Line Tools provide the Swift compiler and Apple SDKs.

## 3. FFmpeg: required or optional?

**FFmpeg is not required by the current app runtime.** The app records microphone audio as WAV using SoundFile and system audio as M4A using Apple's ScreenCaptureKit/AVFoundation helper. MLX Whisper reads those files directly.

FFmpeg is useful as an optional diagnostic/conversion tool when inspecting recordings or converting an audio file manually:

```bash
brew install ffmpeg
ffmpeg -version
```

Example: convert an M4A recording to mono 16 kHz WAV for inspection/testing:

```bash
ffmpeg -i input.m4a -ac 1 -ar 16000 -c:a pcm_s16le output.wav
```

Do not add FFmpeg to the Python requirements; it is a separate command-line utility and is not invoked by the app's normal recording/transcription path.

## 4. Run the app

From the project root, with the virtual environment active:

```bash
python main.py
```

On first transcription, MLX Whisper downloads the configured model from Hugging Face. This is a one-time model download; inference is local afterwards. Ollama models are also stored locally.

## 5. Main window and live answers

Interview Copilot uses one application window; it does not create a separate floating answer overlay. The main window requests always-on-top behavior through Qt. Window stacking can vary with macOS Spaces, full-screen apps and system-managed windows.

Typed questions and questions extracted from interview transcripts stream token by token into the **Latest answer** pane while Ollama generates them. The full completed answer is also added to the conversation history. The answer pane scrolls as new text arrives.

## 6. Audio recording controls

### Control + Option + R toggle shortcut

- Press **Control + Option + R** once: begin microphone + system-audio recording.
- Press **Control + Option + R** again: stop recording and begin local transcription.
- You do not need to hold the key.
- The app shows a recording state and changes the button to **Stop recording** while active.
- If the global shortcut is unavailable, click the in-app Start/Stop button.

The global shortcut uses `pynput` and the Control + Option + R combination. macOS may require Accessibility and Input Monitoring permissions for the terminal or Python process that launches the app.

### Microphone selection

Use the Microphone dropdown to select the Mac's built-in microphone, a Bluetooth headset microphone, or another available input device. Use Refresh after connecting/disconnecting a device. The input selector is locked while recording.

### Audio processing flow

1. Control + Option + R starts a new recording session.
2. `sounddevice` captures microphone frames.
3. The Swift ScreenCaptureKit helper captures system audio.
4. When Control + Option + R is pressed again, capture stops and both audio tracks are finalized.
5. `mlx-whisper` transcribes the microphone and system-audio files locally.
6. Transcript text is passed to the local Ollama workflow for cleanup/answer generation.
7. The temporary session directory is deleted after transcription, including when transcription raises an error.

Audio files are written briefly to a uniquely named directory under the operating system's temporary folder. They are **not retained in the project directory**. A later app launch also attempts to remove abandoned session folders left by a crashed process. The transcript may remain visible in the app conversation; this cleanup concerns the intermediate audio files.

## 7. macOS permissions

Grant permissions to the app that launches Python (for example, Terminal or VS Code):

1. **Microphone:** allows capture of your microphone.
2. **Screen & System Audio Recording:** allows ScreenCaptureKit to capture Mac system audio.
3. **Accessibility / Input Monitoring:** may be required for the global Control + Option + R shortcut.
4. Restart the app after changing permissions.

Menu names can vary slightly by macOS version. If system audio does not start, verify Screen & System Audio Recording permission and restart the launching application.

## 8. Capture privacy setting

The main window's **Capture privacy** toggle applies a macOS window-sharing setting to the single Interview Copilot window.

- ON requests exclusion from compatible macOS capture APIs.
- OFF restores the normal sharing setting.
- The setting is reapplied when windows are shown.

This is not a universal invisibility or anti-capture feature. Apple's current documentation describes `NSWindowSharingNone` as a legacy value and says not to use it to hide content from capture. Some screen-sharing applications, remote desktop tools, screenshots, recording methods or OS versions may capture the window regardless. Always assume a visible app could be shared and follow workplace rules.

## 9. Project layout

```text
.
├── audio/
│   ├── controller.py              # Microphone/system capture lifecycle and Control + Option + R toggle
│   ├── macos_system_audio.swift   # ScreenCaptureKit + AVFoundation recorder
│   ├── transcriber.py             # Local MLX Whisper wrapper
│   └── README.md                  # Audio subsystem notes
├── core/
│   ├── answer_generator.py        # Answer orchestration
│   ├── context_refiner.py         # Transcript refinement
│   ├── document_loader.py         # PDF/DOCX/TXT/MD extraction
│   ├── ollama_client.py           # Local Ollama client
│   ├── prompts.py                 # Prompt templates
│   └── resume_rag.py              # Local resume retrieval
├── ui/
│   ├── macos_window_privacy.py    # macOS window capture setting
│   ├── main_window.py             # Main PySide6 UI
│   └── worker.py                  # Background task worker
├── assets/
│   └── interview-copilot.svg      # App icon
├── requirements.txt               # Core Python dependencies
├── requirements-audio-macos.txt   # Optional macOS audio dependencies
└── main.py                        # Application entry point
```

## 10. Troubleshooting

### Python crashes with segmentation fault

Native extensions can crash the interpreter without a Python traceback. Confirm the active interpreter and architecture:

```bash
which python
python --version
python -c "import platform; print(platform.machine())"
```

Use a fresh Python 3.12 virtual environment and reinstall both requirements files. Do not mix packages from a system Python and a different virtual environment.

For a native crash trace:

```bash
python -X faulthandler main.py
```

### Control + Option + R does not work

- Use the in-app recording button to confirm audio capture works independently.
- Grant Accessibility and Input Monitoring permissions to Terminal/VS Code/Python as applicable.
- Restart the app after granting permissions.
- Check that another application or macOS shortcut is not intercepting Control + Option + R.

### No microphone audio

- Confirm the selected input device in the dropdown.
- Check macOS Microphone permission.
- Click Refresh after connecting a Bluetooth headset.
- Test with the Mac's built-in microphone.

### No system audio

- Confirm macOS 13+.
- Grant Screen & System Audio Recording permission.
- Install Xcode Command Line Tools.
- Restart the terminal/IDE and app after granting permission.

### Whisper model download or transcription issue

- Confirm Apple Silicon and a supported Python environment.
- Check internet access for the first model download.
- Subsequent transcription runs locally using the downloaded model.
- Inspect the audio file with FFmpeg if needed; FFmpeg is optional.

### Ollama offline

```bash
ollama serve
ollama list
```

Ensure `qwen3:8b` and `nomic-embed-text` are present.

## 11. Local data and security

- Resume embeddings are stored locally in SQLite under `vector_db/`.
- Ollama models and the MLX Whisper model are stored in their respective local model caches.
- Audio recordings are temporary files and are removed after transcription.
- Do not commit resumes, transcripts, temporary audio, credentials or local databases.
- `data/`, `vector_db/`, virtual environments and Python cache files are ignored by Git.

## 12. Updating

```bash
git switch feature/single-window-live-responses
git pull origin feature/single-window-live-responses
source .venv/bin/activate
python main.py
```

If dependencies changed in a later update, reinstall the requirements files.

## License

No license has been added yet. Contact the repository owner before redistributing.
