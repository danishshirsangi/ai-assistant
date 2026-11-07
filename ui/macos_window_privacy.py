import sys
from ctypes import c_void_p


def set_window_capture_exclusion(widget, excluded=True):
    """Apply macOS NSWindow sharing policy to a Qt window.

    This is a best-effort exclusion for capture APIs that honor
    NSWindowSharingNone. It is not a guarantee against every recorder.
    """
    if sys.platform != "darwin":
        return False, "Window capture privacy is supported on macOS only."

    try:
        import AppKit
        import objc

        native_view = objc.objc_object(c_void_p=int(widget.winId()))
        native_window = native_view.window()
        if native_window is None:
            return False, "Could not access the native macOS window."

        sharing = (
            AppKit.NSWindowSharingNone
            if excluded else AppKit.NSWindowSharingReadOnly
        )
        native_window.setSharingType_(sharing)
        return True, "Applied" if excluded else "Capture allowed"
    except Exception as exc:
        return False, str(exc)
