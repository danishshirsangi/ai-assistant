

https://github.com/user-attachments/assets/e6f60759-1019-4020-9b90-d6465fca0141



# AI Meeting Assistant

A macOS desktop assistant for interview preparation and meeting support. It can accept typed questions or record your microphone and Mac system audio, transcribe the audio locally with Whisper, and use Google Gemini to generate an answer.

This README is a complete first-time installation guide for a Mac. Follow the steps in order. You do not need to know Python to install and run the application, but you will need to copy commands into Terminal.

> **Current implementation note:** typed questions each get their own selectable entry in the Questions sidebar. Audio is currently processed after you stop a recording; one recording session creates one sidebar entry and one generated answer. A single uninterrupted one-hour recording is not yet divided into separate entries for each question.

---

## 1. What the application does

- Provides a desktop interface built with Python and PySide6.
- Uses **Gemini 3.5 Flash-Lite** to generate answers.
- Uses **Gemini Embedding 2** to search relevant sections of your uploaded resume.
- Stores the resume search index locally in SQLite so you do not have to upload the same resume every time you reopen the app.
- Records microphone input and Mac system audio.
- Uses **MLX Whisper locally on Apple Silicon** to transcribe the recorded audio.
- Sends the transcript, question, conversation context and relevant resume excerpts to Gemini to generate an answer.
- Displays questions in a selectable sidebar. Selecting a question displays its saved answer.
- Provides keyboard shortcuts to start/stop recording and hide/restore the app.

### Important: what is and is not live

The current audio workflow is **record → stop → transcribe locally → send transcript to Gemini → display answer**. It does not continuously detect every interviewer question during a call. It also does not show a live transcript in the UI. See [Current limitations](#14-current-limitations) before relying on it in an interview.

---

## 2. Before you start: system requirements

This version is designed for:

- **Mac with Apple Silicon**: M1, M2, M3, M4, M5 or later.
- **macOS 13 (Ventura) or later**.
- **Python 3.12**.
- Internet connection for installation, Gemini requests and the first Whisper model download.
- Permission to install developer command-line tools and applications on your Mac.

Check your Mac before installing:

1. Open **Finder → Applications → Utilities → Terminal**.
2. Open Terminal.
3. Copy and run:

```bash
uname -m
sw_vers -productVersion
```

For this audio-enabled version, `uname -m` should print `arm64`. The macOS version should be 13 or newer.

---

## 3. Applications and tools you need

You do not need to install a large development environment. These are the tools used by the current code.

| Tool | Required? | Why it is needed |
|---|---|---|
| **Terminal** | Yes | Included with macOS. Used to install, configure and launch the app. |
| **Xcode Command Line Tools** | Yes | Provides Git, Swift compiler (`swiftc`) and Apple build tools. The app compiles its small Swift audio-capture helper the first time you record. |
| **Homebrew** | Recommended | macOS package manager used here to install Python 3.12. |
| **Python 3.12** | Yes | Runs the desktop application and its Python packages. |
| **Git** | Yes | Downloads the project and lets you update it. Git is included with Xcode Command Line Tools. |
| **Google AI Studio account and Gemini API key** | Yes | Authenticates Gemini answer generation and resume embeddings. |
| **Visual Studio Code** | Optional | A convenient editor for viewing the project and editing `.env`. You can use TextEdit or Terminal instead. |

### Not required for this version

- **Full Xcode app:** not required; Xcode Command Line Tools are enough.
- **FFmpeg:** not required by the current recording or transcription code.
- **Docker:** not used.
- **Node.js / npm:** not used.
- **Ollama:** not used by the Gemini application flow. The old Ollama client file is retained in the repository, but this branch uses Gemini.

---

## 4. Install Xcode Command Line Tools

The app uses Apple's ScreenCaptureKit API to capture Mac system audio. A small Swift helper is compiled automatically the first time you start recording. You do not need to compile it yourself.

In Terminal, run:

```bash
xcode-select --install
```

A macOS dialog should appear. Click **Install** and accept the licence. Wait for installation to finish.

Verify the tools:

```bash
xcode-select -p
git --version
swift --version
```

You should see an installed developer tools path and version information. If macOS says the command-line tools are already installed, continue.

Apple's guide: [Install Xcode Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools).

---

## 5. Install Homebrew

Homebrew is used to install the recommended Python version.

In Terminal, copy and run the official installer:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. The installer may ask for your Mac login password. When you type a password in Terminal, the characters do not appear; this is normal.

For Apple Silicon Macs, add Homebrew to your Terminal path:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Check that Homebrew works:

```bash
brew --version
```

If Terminal says `brew: command not found`, close Terminal, open it again and run `brew --version`. If it still fails, check the Homebrew installation instructions: [brew.sh](https://brew.sh/).

---

## 6. Install Python 3.12

Use Homebrew to install Python 3.12:

```bash
brew install python@3.12
```

Verify the installed version:

```bash
"$(brew --prefix python@3.12)/bin/python3.12" --version
```

The output should begin with `Python 3.12`.

**Use Python 3.12 for this project.** MLX Whisper and other native dependencies need compatible Apple Silicon wheels. Do not use the macOS system Python, and do not use a very new Python version just because it is already installed.

---

## 7. Download the AI Meeting Assistant project

Choose a folder where you want to keep the project. For example, your Desktop:

```bash
cd ~/Desktop
```

Clone the Gemini version of the repository:

```bash
git clone https://github.com/danishshirsangi/ai-assistant.git
```

Enter the project folder:

```bash
cd ai-assistant
```

Check that you are on the correct branch:

```bash
git branch --show-current
```

It should print:

```text
main
```

> **Important:** The official application is on the `main` branch. A normal clone downloads this version automatically.

---

## 8. Create a Python virtual environment

A virtual environment keeps this project's Python packages separate from other projects on your Mac.

From inside the `ai-assistant` folder, run:

```bash
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Your Terminal prompt will usually show `.venv` when it is active.

Verify:

```bash
python --version
which python
```

The Python version should be 3.12, and the Python path should point inside the project's `.venv` directory.

**Whenever you open a new Terminal window to work on this project, activate the environment again:**

```bash
cd ~/Desktop/ai-assistant
source .venv/bin/activate
```

If you cloned the project somewhere else, use that folder's path instead.

---

## 9. Install the Python packages

First update the Python package installer:

```bash
python -m pip install --upgrade pip wheel setuptools
```

Install the main application dependencies:

```bash
python -m pip install -r requirements.txt
```

Install the macOS audio and local transcription dependencies:

```bash
python -m pip install -r requirements-audio-macos.txt
```

### What these packages are for

| Package | Purpose |
|---|---|
| `PySide6` | Desktop application UI |
| `google-genai` | Gemini API connection |
| `python-dotenv` | Reads the Gemini key from the local `.env` file |
| `PyMuPDF` | Reads text from PDF resumes |
| `python-docx` | Reads DOCX resumes |
| `sounddevice` | Records your microphone |
| `soundfile` | Writes temporary microphone audio files |
| `numpy` | Handles microphone audio data |
| `pynput` | Listens for the global keyboard shortcuts |
| `mlx-whisper` | Runs Whisper transcription locally on Apple Silicon |
| `pyobjc-framework-Cocoa` | macOS window integration |

The installer may take some time because MLX and other packages contain native components. Let it finish. If the command ends with an error, keep the complete Terminal output for troubleshooting.

---

## 10. Create your Gemini API key

The app needs a Gemini API key to generate answers and create resume embeddings.

1. Open [Google AI Studio – API Keys](https://aistudio.google.com/api-keys).
2. Sign in with your Google account.
3. Select an existing project or create a new project when prompted.
4. Click **Create API key**.
5. Copy the key and keep it private.

Google's current key guidance: [Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key).

### Free tier and billing

For a new project, check its tier in Google AI Studio before using it. This application is configured for the standard Gemini Developer API models listed below. Google lists free-tier access for both the configured chat model and embedding model, subject to model availability and project quotas.

- **Do not click “Set up billing”** if you intend to stay on the Free Tier.
- Check your actual project tier, active quotas and usage in [Google AI Studio](https://aistudio.google.com/).
- Quotas are project- and model-specific and can change. The app cannot guarantee a particular number of free requests.
- If you link a paid billing account or use a paid tier, applicable charges may apply.

Google's live documentation: [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits).

> **Privacy warning:** Google's current Gemini API pricing page says content submitted on the Free Tier may be used to improve Google products. Your resume text, interview transcript, questions, conversation context and retrieved resume excerpts are sent to Gemini. Do not use confidential employer/client information, private meeting content or sensitive personal data unless you have reviewed Google's terms and have permission to share it. Paid-tier data-use terms are different; check Google's current documentation rather than assuming.

---

## 11. Add the Gemini API key to the application

Make sure your Terminal is inside the project folder (`ai-assistant`) and your virtual environment is active.

Create your local environment file:

```bash
cp .env.example .env
```

Open it in the Terminal text editor:

```bash
nano .env
```

The file contains these settings:

```dotenv
GEMINI_API_KEY=your_google_ai_studio_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

Replace only the first value with the API key you copied from Google AI Studio. Keep the model names as shown unless you intentionally want to configure another model supported by your API project.

Example format (this is a placeholder, not a working key):

```dotenv
GEMINI_API_KEY=PASTE_YOUR_KEY_HERE
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

Save the file in `nano`:

1. Press **Control + O**.
2. Press **Enter** to confirm the file name.
3. Press **Control + X** to exit.

Restrict access to the key file:

```bash
chmod 600 .env
```

The `.env` file is excluded by `.gitignore`. **Never commit it, upload it to GitHub, paste it into an issue, or share a screenshot that shows the key.** If you accidentally expose the key, revoke it in Google AI Studio and create a new one.

---

## 12. Test your Gemini connection

Before opening the desktop application, test the API.

Make sure the virtual environment is active, then run:

```bash
python diagnostics/gemini_smoke_test.py
```

The diagnostic checks:

1. Whether the API key is loaded.
2. Whether the configured chat model can be reached.
3. Whether Gemini Embedding 2 can create a test embedding.
4. Whether Gemini can stream a short text response.

A successful run ends with:

```text
PASS: API check, embeddings and text generation all succeeded.
```

If this test fails, do not continue to audio troubleshooting yet. First check the API key, project tier, internet connection and the error shown in Terminal.

---

## 13. Launch the application

From the project root, with `.venv` active, run:

```bash
python main.py
```

The **AI Meeting Assistant** window should open.

The app runs as a macOS accessory application. It may not appear in the Dock or in the normal Command-Tab app switcher. Keep the Terminal session open while using the app. To quit, close the app or press **Control + C** in the Terminal that launched it.

### First-time resume upload

1. Click **Upload resume**.
2. Select a resume in one of these formats: PDF, DOCX, TXT or MD.
3. Wait for the **Resume indexed with Gemini** status and the confirmation message.
4. Start asking questions.

The app extracts text, divides it into smaller sections, sends those sections to Gemini Embedding 2 and stores the indexed text and vectors in:

```text
ai-assistant/
└── vector_db_gemini/
    └── resume_vectors.sqlite3
```

You only need to upload the same resume again when you want to replace it, or if you have deleted/moved the local index. Restarting the app does not normally require another upload.

The original resume file is not stored in that folder; the database contains searchable text sections, filenames and embeddings. Resume text is sent to Google's API when the embeddings are created.

---

## 14. macOS permissions for recording and shortcuts

Typed questions can be used without enabling microphone or system-audio capture. To use recording, macOS must give the application that launched Python the required permissions.

Open:

**Apple menu → System Settings → Privacy & Security**

Depending on your macOS version, enable the following permissions for **Terminal**, **VS Code** or the application you use to launch `python main.py`.

| macOS permission | Why the app needs it |
|---|---|
| **Microphone** | Captures your voice. |
| **Screen & System Audio Recording** (wording may vary) | Allows Apple's ScreenCaptureKit to capture audio playing through your Mac. |
| **Accessibility** | May be needed for global keyboard monitoring. |
| **Input Monitoring** | May be needed for the global keyboard shortcuts. |

After changing permissions:

1. Quit the app.
2. Quit and reopen Terminal (or your IDE).
3. Run `python main.py` again.
4. If macOS asks for permission, approve it.

If the global shortcuts do not work, use the on-screen recording and hide buttons while you troubleshoot the permissions.

---

## 15. How to use the application

### Ask a typed question

1. Type a question in the input field at the bottom.
2. Press **Enter** or click **Generate answer**.
3. Gemini searches the saved resume index and generates an answer.
4. The newest question appears in the left **Questions** sidebar.
5. Click an older question to display its saved answer again.

### Record a meeting or interview

- Press **Control + Option + R** once to start recording.
- Press **Control + Option + R** again to stop recording.
- You can also use the on-screen **Start recording / Stop recording** button.
- Choose the microphone from the dropdown if you do not want to use the macOS default microphone.
- After stopping, the app transcribes the microphone and system audio locally and sends the transcript to Gemini to generate an answer.

### Hide and restore the window

- Press **Control + Option + H** to hide the whole app window.
- Press **Control + Option + H** again to restore it.
- You can also use the **Hide window** button when the app is visible.

Hiding the window does not stop a recording or quit the app.

### Clear the current session

Click **Clear session** to clear the visible question list, answers and in-memory conversation context. This does **not** delete your saved resume index or your Gemini API key.

---

## 16. First-time audio setup and Whisper model download

On the first recording, the app compiles its Swift ScreenCaptureKit helper automatically. Xcode Command Line Tools must be installed for this to work.

On the first transcription, MLX Whisper downloads the configured model:

```text
mlx-community/whisper-base-mlx
```

The download is managed by the Hugging Face model cache. It requires an internet connection and happens only when the model is not already cached. Later transcriptions use the cached model locally.

The transcription language is currently configured as **English**.

The capture files are written temporarily in a macOS temporary directory. The app removes them after transcription. The recognized transcript is sent to Gemini for answer generation; the raw audio files are not sent to Gemini by this workflow.

FFmpeg is not used by the current normal recording or transcription path.

---

## 17. Current limitations

Please understand these limitations before using the app in a live interview:

1. **Audio is processed after you stop recording.** The app does not yet continuously transcribe and answer each question during a recording.
2. **One recording session creates one sidebar item.** A one-hour recording with many questions is currently treated as one transcript and one generated answer. It is not automatically split into one entry per interviewer question.
3. **Typed questions are separate.** Each typed question creates its own sidebar item and can be revisited.
4. **Whisper language is set to English.** Other languages may be transcribed inaccurately.
5. **Gemini requires internet access.** Local transcription does not mean answer generation is fully offline.
6. **AI can make mistakes.** Verify important technical answers, SQL, figures and claims rather than treating generated answers as guaranteed facts.
7. **Always-on-top and capture privacy are best-effort.** macOS Spaces, full-screen applications and meeting software may behave differently. Do not assume the assistant is hidden from screen sharing or recording.

Only record a meeting when participant consent, applicable law and your employer's policy allow it.

---

## 18. Troubleshooting

### A. `brew: command not found`

Close and reopen Terminal, then run:

```bash
eval "$(/opt/homebrew/bin/brew shellenv)"
brew --version
```

If it still fails, revisit [Homebrew installation](https://brew.sh/).

### B. `python: command not found` or the wrong Python version

Make sure Python 3.12 is installed and the project's virtual environment is active:

```bash
"$(brew --prefix python@3.12)/bin/python3.12" --version
source .venv/bin/activate
python --version
which python
```

If you created `.venv` using a different Python version, remove and recreate it:

```bash
deactivate
rm -rf .venv
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt
python -m pip install -r requirements-audio-macos.txt
```

### C. `ModuleNotFoundError` when launching the app

Activate `.venv`, then reinstall the requirements:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-audio-macos.txt
```

### D. Gemini says the API key is missing

- Make sure the file is named exactly `.env`, not `.env.txt`.
- Make sure it is in the top-level `ai-assistant` folder, next to `main.py`.
- Make sure the key line begins with `GEMINI_API_KEY=`.
- Do not put spaces around the equals sign.
- Restart the application after editing the file.
- Run `python diagnostics/gemini_smoke_test.py` and read the first failing step.

### E. Gemini returns 401, 403, 404 or 429 errors

- **401 / 403:** check that the key is valid, has not been revoked and belongs to a project with Gemini API access.
- **404 / model not found:** check the model name in `.env` and confirm that it is available for your API project.
- **429 / quota exceeded:** check the active model/project limits in [AI Studio Rate Limits](https://aistudio.google.com/usage). Wait for the applicable limit to reset or review the project's tier. Do not assume every account has the same quota.

### F. Audio recording does not start

- Confirm macOS 13 or newer.
- Confirm Xcode Command Line Tools are installed: `xcode-select -p`.
- Confirm **Microphone** and **Screen & System Audio Recording** permissions.
- Quit and reopen the launching app (Terminal or IDE).
- Try the on-screen Start recording button if the keyboard shortcut does not work.

### G. System audio is missing

- Make sure audio is actually playing through the Mac while recording.
- Check **Screen & System Audio Recording** permission.
- Stop recording and check the error shown by the application.
- Reopen Terminal after changing macOS permissions.

### H. Control + Option + R or Control + Option + H does not work

- Check Accessibility and Input Monitoring permissions for the app that launches Python.
- Restart that launching app after changing permissions.
- Use the in-app buttons as a fallback.
- Check whether another macOS shortcut or application is using the same key combination.

### I. First transcription takes a long time

The first transcription may download the Whisper model. Keep the Mac connected to the internet and wait for the download to finish. Subsequent runs should reuse the cached model.

### J. The application window is blank or does not display correctly

Update to the latest commit on `main`, activate `.venv` and relaunch. If it remains blank, run:

```bash
python -X faulthandler main.py
```

Share the full Terminal output and a screenshot of the window when reporting the issue. Do not share your `.env` file or API key.

---

## 19. Project files and local data

| Path | Description |
|---|---|
| `.env` | Your private Gemini API key and model settings. Never commit it. |
| `.env.example` | Safe template showing the required environment variables. |
| `.venv/` | Project's isolated Python environment. |
| `vector_db_gemini/resume_vectors.sqlite3` | Local resume text chunks and embedding vectors. |
| `data/bin/system_audio_capture` | Swift audio helper compiled on first use. |
| macOS temporary directory | Temporary microphone/system audio files, removed after transcription. |

These local files and folders are excluded from Git where appropriate. Back up `.env` securely if you need to preserve your API configuration, and back up `vector_db_gemini/` if you want to keep the resume index.

---

## 20. Update the application

When a new version is pushed to the Gemini branch, open Terminal and run:

```bash
cd ~/Desktop/ai-assistant
git switch main
git pull origin main
source .venv/bin/activate
```

If the update changes Python dependencies, reinstall them:

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-audio-macos.txt
```

Then launch:

```bash
python main.py
```

If the project is stored somewhere other than your Desktop, change the `cd` path accordingly.

---

## 21. Quick start checklist

Use this checklist after following the full guide:

- [ ] Apple Silicon Mac with macOS 13 or newer.
- [ ] Xcode Command Line Tools installed.
- [ ] Homebrew installed and working.
- [ ] Python 3.12 installed.
- [ ] Repository cloned on `main`.
- [ ] Virtual environment created and activated.
- [ ] Both Python requirements files installed.
- [ ] Gemini API key added to the root `.env` file.
- [ ] Gemini diagnostic ends with `PASS`.
- [ ] Application opens with `python main.py`.
- [ ] Resume uploaded and indexed.
- [ ] macOS microphone, system-audio and shortcut permissions granted.
- [ ] A short test recording successfully transcribes and generates an answer.

---

## Official installation and API resources

- [Homebrew installation](https://brew.sh/)
- [Apple Xcode Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools)
- [Python 3.12 downloads](https://www.python.org/downloads/)
- [Git for macOS](https://git-scm.com/install/mac)
- [Google AI Studio API Keys](https://aistudio.google.com/api-keys)
- [Gemini API key guide](https://ai.google.dev/gemini-api/docs/api-key)
- [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)

## License

No license has been added to this repository yet. Contact the repository owner before redistributing the application.


---

## Build a standalone macOS application (Apple Silicon)

You can package the project as **AI Meeting Assistant.app** and a drag-and-drop **AI Meeting Assistant.dmg** installer. After installation, launch it from Applications or the Dock; you do not need to run `python main.py` for normal use.

### Requirements for the one-time build

- Apple Silicon Mac (M1 or newer), running macOS 13 or later.
- Python 3.12.
- Xcode Command Line Tools (the build uses `swiftc` for the ScreenCaptureKit audio helper).
- Internet access to download Python packages and the Whisper model on first use.

### Build

From the project folder, check out the packaging branch and run:

```bash
git fetch origin
git switch fix/complete-long-responses 2>/dev/null || git switch --track origin/fix/complete-long-responses
git pull origin fix/complete-long-responses
chmod +x build_macos_app.sh
PYTHON_BIN="$(brew --prefix python@3.12)/bin/python3.12" ./build_macos_app.sh
```

The first build can take several minutes. PyInstaller creates a self-contained app bundle and the script creates:

```text
dist/
├── AI Meeting Assistant.app
└── AI Meeting Assistant.dmg
```

Open the DMG, drag **AI Meeting Assistant** to **Applications**, eject the DMG, then launch the app from Applications. The build is currently unsigned and not notarized. On first launch, macOS may block it: Control-click the app in Finder, choose **Open**, and confirm. This is intended for personal use on the Mac that built it, not public distribution.

### First launch and data

- Enter your Gemini API key in the first-run setup window. The key is saved with owner-only file permissions in `~/Library/Application Support/AI Meeting Assistant/.env`.
- Resume indexes are stored under `~/Library/Application Support/AI Meeting Assistant/vector_db_gemini/`.
- The app bundle contains the Python runtime and dependencies, plus the precompiled Swift system-audio helper. It does not include your Gemini API key or Whisper model weights.
- The Whisper model is downloaded and cached on first transcription. An internet connection is required for Gemini requests.
- Grant Microphone, Screen & System Audio Recording, Accessibility and Input Monitoring permissions when macOS requests them. You may need to grant permissions to **AI Meeting Assistant** itself and restart it.
- Screen capture protection remains best-effort and does not guarantee invisibility in every screen recorder or meeting app.

### Updating

Build a new app from the latest branch using the same command, then replace the older copy in Applications with the new one. Your API key and resume index remain in Application Support.

### Troubleshooting the build

- If the script says Python 3.12 is missing, install it with `brew install python@3.12`.
- If Swift compilation fails, install or repair Xcode Command Line Tools with `xcode-select --install`.
- If the app opens but recording fails, check macOS privacy permissions and try again.
- This packaging setup has been added to the repository, but the actual app bundle must be built and tested on an Apple Silicon Mac. A successful GitHub commit alone does not confirm the packaged app runs.
