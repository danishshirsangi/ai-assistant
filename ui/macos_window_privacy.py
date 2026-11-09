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


def apply_window_glass_effect(widget):
    """Install a native macOS blurred material behind the translucent Qt UI.

    Qt stylesheet translucency remains the fallback on platforms or macOS
    versions where NSVisualEffectView cannot be attached.
    """
    if sys.platform != "darwin":
        return False, "Native glass material is available on macOS only."

    if getattr(widget, "_glass_effect_view", None) is not None:
        return True, "Already applied"

    try:
        import AppKit
        import objc

        native_view = objc.objc_object(c_void_p=int(widget.winId()))
        native_window = native_view.window()
        if native_window is None:
            return False, "Could not access the native macOS window."

        content_view = native_window.contentView()
        material_view = AppKit.NSVisualEffectView.alloc().initWithFrame_(
            content_view.bounds()
        )
        material = getattr(AppKit, "NSVisualEffectMaterialHUDWindow", None)
        if material is None:
            material = getattr(AppKit, "NSVisualEffectMaterialSidebar", 7)
        material_view.setMaterial_(material)
        material_view.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        material_view.setState_(AppKit.NSVisualEffectStateActive)
        material_view.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )

        native_window.setOpaque_(False)
        native_window.setBackgroundColor_(AppKit.NSColor.clearColor())
        content_view.addSubview_positioned_relativeTo_(
            material_view, AppKit.NSWindowBelow, None
        )
        # Keep the PyObjC wrapper alive for the lifetime of the window.
        widget._glass_effect_view = material_view
        return True, "Native macOS glass material applied."
    except Exception as exc:
        return False, str(exc)
