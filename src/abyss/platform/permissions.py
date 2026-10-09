"""État des autorisations système (micro). macOS via le runtime Objective-C (ctypes), sans dépendance."""

from __future__ import annotations

import ctypes
import ctypes.util
import sys

# Valeurs AVAuthorizationStatus
NOT_DETERMINED, RESTRICTED, DENIED, AUTHORIZED = 0, 1, 2, 3


def microphone_status() -> str:
    """'authorized' | 'denied' | 'not_determined' | 'unknown' (hors macOS ou en cas d'échec)."""
    if sys.platform != "darwin":
        return "unknown"
    try:
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        av = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AVFoundation.framework/AVFoundation")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = objc.objc_msgSend
        send.restype = ctypes.c_long
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        cls = objc.objc_getClass(b"AVCaptureDevice")
        sel = objc.sel_registerName(b"authorizationStatusForMediaType:")
        media = ctypes.c_void_p.in_dll(av, "AVMediaTypeAudio")
        status = send(cls, sel, media)
    except Exception:
        return "unknown"
    return {AUTHORIZED: "authorized", DENIED: "denied", RESTRICTED: "denied",
            NOT_DETERMINED: "not_determined"}.get(status, "unknown")
