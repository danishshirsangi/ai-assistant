# Interview Copilot — macOS MVP

A local-first interview assistant built with Python, PySide6, Ollama and SQLite.

## What works in v0.1

- Native desktop chat window.
- Separate always-on-top floating answer window.
- Connects to a local Ollama server.
- Uploads PDF, DOCX, TXT or Markdown resumes.
- Extracts text, chunks it, embeds it with Ollama and stores vectors in local SQLite.
- Retrieves relevant resume context for each question.
- Answers general questions even when they are not covered by the resume.
- Maintains recent conversation history.
- Adaptive answer style and safeguards against inventing personal experience.

## Requirements

- macOS
- Python 3.10+
- Ollama installed and running
- Models:
  - `qwen3:8b`
  - `nomic-embed-text`

Install / prepare Ollama:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama serve
```

If Ollama is already running as a macOS app, you usually do not need to run
`ollama serve` again. Check with `ollama list`.

## Setup

From this project directory:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

## First run

1. Confirm the status says `Ollama connected`.
2. Click **Upload resume** and select your PDF or DOCX.
3. Wait for local indexing to finish.
4. Ask a question such as:
   - "Walk me through my analytics experience."
   - "How would you investigate a 10% drop in orders in one city?"
   - "Explain how campaign uplift analysis works."
5. Click **Show floating overlay** to open the separate always-on-top answer window.

## Local storage

- `vector_db/resume_vectors.sqlite3` contains the local SQLite vector index.
- Your resume is not uploaded to a cloud service by this application.
- Do not commit `data/`, `vector_db/` or your resume to source control.

## Current limitations

- v0.1 is text-first. It does not yet record microphone or system audio.
- The floating overlay is a normal visible window, not a stealth/hidden window.
- No automatic answer generation from live calls yet.
- The initial build uses synchronous Ollama HTTP calls in background workers.
- Resume extraction is text-based; scanned PDFs may need OCR in a later version.

## Next milestone: audio

See `audio/README.md`. We will add push-to-talk, local Whisper transcription,
macOS ScreenCaptureKit system audio capture and a context-refinement stage.
