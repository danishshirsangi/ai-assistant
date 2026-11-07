# Interview Copilot — macOS local-first assistant

A local-first interview assistant built with Python, PySide6, Ollama and SQLite.

## v0.1
- Native desktop chat and always-on-top floating answer window.
- Local Ollama chat and embeddings.
- PDF, DOCX, TXT and Markdown resume indexing in SQLite.
- Resume-aware answers plus general Business/Data Analyst interview reasoning.
- Recent conversation context and safeguards against inventing personal experience.

## v0.2 audio milestone
- Hold the **Control** key anywhere to start recording; release it to stop.
- Captures microphone audio using sounddevice.
- Captures macOS system audio using Apple's ScreenCaptureKit (macOS 13+).
- Transcribes both tracks locally using MLX Whisper on Apple Silicon.
- Keeps microphone and system-audio transcripts separately labelled.
- Cleans filler/repetition while preserving technical terms, numbers, negations and follow-up references.
- Generates an answer in the main window and floating overlay.
- Includes a visible recording state and manual Start/Stop fallback.

## Requirements
- macOS 13+ for ScreenCaptureKit system-audio capture.
- Apple Silicon for the MLX Whisper transcription path.
- Python 3.10+.
- Ollama running locally with `qwen3:8b` and `nomic-embed-text`.
- Xcode Command Line Tools: `xcode-select --install`.

Prepare Ollama:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

## Update an existing clone

From the existing repository folder:

```bash
git fetch origin
git switch -c feature/v0.2-audio-copilot --track origin/feature/v0.2-audio-copilot
```

If you already created the local branch, use `git pull` after switching to it.

Activate your existing virtual environment and install the audio dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-audio-macos.txt
```

Run:

```bash
python main.py
```

On first use, MLX Whisper downloads its model files once. Transcription and inference run locally afterwards; audio and transcripts are not sent to a cloud API.

## macOS permissions
1. Allow Microphone access when prompted.
2. Allow Screen & System Audio Recording for the terminal/Python app running ScreenCaptureKit.
3. Allow Accessibility (and, if prompted, Input Monitoring) for the global Control shortcut.
4. Restart the app after changing permissions.

The app displays a visible recording state. Only record calls when all participants and applicable workplace policies permit it.

## Local data
- `vector_db/resume_vectors.sqlite3`: local resume embeddings.
- `data/audio_sessions/`: local microphone WAV and system-audio M4A recordings.
- `data/bin/`: locally compiled ScreenCaptureKit helper.
- These paths are ignored by Git. Do not commit resumes, transcripts or recordings.

## Known limitations
- Transcription begins after releasing Control; this is not live streaming.
- English is the default Whisper language.
- System audio capture requires macOS 13+ and Screen & System Audio Recording permission.
- Global Control may require Accessibility/Input Monitoring permission.
- Scanned PDF OCR and configurable shortcuts are future improvements.
