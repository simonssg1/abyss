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


def set_dock_name(name: str) -> None:
    """Nom du Dock et du Moniteur d'activité (sinon « python3.11 »).

    API privée LaunchServices (celle de Firefox et Chromium pour leurs processus) : le processus n'étant pas
    un bundle, seul ce nom d'affichage peut être changé. À appeler une fois l'app enregistrée (fenêtre créée).
    """
    if sys.platform != "darwin":
        return
    try:
        ls = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        ls._LSGetCurrentApplicationASN.restype = ctypes.c_void_p
        ls._LSSetApplicationInformationItem.restype = ctypes.c_int
        ls._LSSetApplicationInformationItem.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                                        ctypes.c_void_p, ctypes.c_void_p]
        asn = ls._LSGetCurrentApplicationASN()
        if not asn:
            return
        key = ctypes.c_void_p.in_dll(ls, "_kLSDisplayNameKey")
        value = cf.CFStringCreateWithCString(None, name.encode(), 0x08000100)  # kCFStringEncodingUTF8
        ls._LSSetApplicationInformationItem(-2, asn, key, value, None)  # -2 = kLSDefaultSessionID
    except Exception:
        pass
