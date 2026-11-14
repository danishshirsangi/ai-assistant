"""Paths for development and packaged macOS application runs."""
import sys
from pathlib import Path


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


def resource_path(relative_path: str) -> Path:
    """Return a bundled resource path in both development and PyInstaller builds."""
    return project_root() / relative_path


def app_data_dir() -> Path:
    """Return a writable, persistent per-user application data directory."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    path = base / "AI Meeting Assistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


def env_file_path() -> Path:
    """Prefer the per-user key/config file; retain root .env for development."""
    user_env = app_data_dir() / ".env"
    if user_env.exists() or getattr(sys, "frozen", False):
        return user_env
    return project_root() / ".env"
