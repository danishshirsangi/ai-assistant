# PyInstaller build definition for Apple Silicon macOS.
from PyInstaller.utils.hooks import collect_all

datas = [
    ("assets", "assets"),
    ("audio/macos_system_audio.swift", "audio"),
]
binaries = [
    ("build_support/system_audio_capture", "audio"),
]
hiddenimports = []

# MLX/Whisper and the Google SDK use package resources and dynamic imports.
for package in (
    "mlx",
    "mlx_whisper",
    "sounddevice",
    "soundfile",
    "google.genai",
    "huggingface_hub",
    "transformers",
    "tokenizers",
    "PySide6",
    "objc",
    "AppKit",
):
    try:
        package_datas, package_binaries, package_hiddenimports = collect_all(package)
        datas += package_datas
        binaries += package_binaries
        hiddenimports += package_hiddenimports
    except Exception:
        # Some optional subpackages are not present on every supported version.
        pass

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI Meeting Assistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="AI Meeting Assistant",
)

app = BUNDLE(
    coll,
    name="AI Meeting Assistant.app",
    icon=None,
    bundle_identifier="com.danishshirsangi.aimeetingassistant",
    info_plist={
        "CFBundleDisplayName": "AI Meeting Assistant",
        "LSMinimumSystemVersion": "13.0",
        "NSMicrophoneUsageDescription": "AI Meeting Assistant uses the microphone to record and transcribe your meeting audio locally.",
        "NSScreenCaptureUsageDescription": "AI Meeting Assistant uses ScreenCaptureKit to capture system audio during a recording.",
        "NSHighResolutionCapable": True,
    },
)
