"""Petits réglages macOS via le runtime Objective-C (ctypes), sans dépendance."""

from __future__ import annotations

import ctypes
import ctypes.util
import sys


def set_process_name(name: str) -> None:
    """Nom affiché dans la barre de menus / le Dock (sinon « Python »). À appeler avant QGuiApplication."""
    if sys.platform != "darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
        ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Foundation.framework/Foundation")
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p

        def msg(obj, sel, *args, argtypes=()):
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, *argtypes]
            return send(obj, objc.sel_registerName(sel), *args)

        nsstring = objc.objc_getClass(b"NSString")
        value = msg(nsstring, b"stringWithUTF8String:", name.encode(), argtypes=(ctypes.c_char_p,))
        key = msg(nsstring, b"stringWithUTF8String:", b"CFBundleName", argtypes=(ctypes.c_char_p,))
        bundle = msg(objc.objc_getClass(b"NSBundle"), b"mainBundle")
        info = msg(bundle, b"infoDictionary")  # NSMutableDictionary en pratique pour un exécutable nu
        if info:
            msg(info, b"setObject:forKey:", value, key, argtypes=(ctypes.c_void_p, ctypes.c_void_p))
    except Exception:
        pass
