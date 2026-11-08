from pathlib import Path

MODEL_REPO = "mlx-community/whisper-base-mlx"


def transcribe_local(audio_path):
    """Transcribe a local audio file with MLX Whisper on Apple Silicon."""
    path = Path(audio_path)
    if not path.exists() or path.stat().st_size < 2048:
        return ""
    try:
        import mlx_whisper
    except ImportError as exc:
        raise RuntimeError(
            "Audio dependencies are missing. Run: "
            "pip install -r requirements-audio-macos.txt"
        ) from exc
    result = mlx_whisper.transcribe(
        str(path), path_or_hf_repo=MODEL_REPO,
        language="en", temperature=0.0, verbose=False,
    )
    return (result.get("text") or "").strip()
