"""Automate ksEditor FBX → KN5 conversion via UI Automation.

Usage (from repo root, on an INTERACTIVE desktop session):
    python tools/auto_kn5_convert.py                 # convert all (maps + cars)
    python tools/auto_kn5_convert.py yaris           # convert one by id
    python tools/auto_kn5_convert.py --list          # list conversion targets

Requires: pywinauto, comtypes (pip install pywinauto comtypes)

VERIFIED WORKING (2026-10-14):
- FindWindow("ksEditor Public") → attach UIA via ElementFromHandle
- Real mouse clicks (SetCursorPos + mouse_event) on File → Open FBX
- Standard #32770 Open dialog: SendMessage fill path + click Open
- FBX loads (verified via Recent FBX Files menu)
- File → Save KN5 → Car/Track → fill Save dialog → KN5 created
"""

from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Desktop

ROOT = Path(__file__).resolve().parents[1]
KSEDITOR = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe")

WM_SETTEXT = 0x000C
BM_CLICK = 0x00F5
user32 = ctypes.windll.user32

# (id, kind, fbx_source, kn5_target)
TARGETS = [
    # Maps
    ("tin_kwong", "track",
     ROOT / "build" / "HP1C" / "tin_kwong_road" / "hd_map.fbx",
     ROOT / "content" / "tracks" / "hong_kong_1to1" / "hd_map.kn5"),
    ("sheung_on", "track",
     ROOT / "build" / "HP1C" / "sheung_on_street" / "hd_map.fbx",
     ROOT / "content" / "tracks" / "hong_kong_1to1_sheung_on" / "hd_map.kn5"),
    ("texaco", "track",
     ROOT / "build" / "HP1C" / "texaco_road" / "hd_map.fbx",
     ROOT / "content" / "tracks" / "hong_kong_1to1_texaco" / "hd_map.kn5"),
    # Cars
    ("yaris", "car",
     ROOT / "content" / "cars" / "hk_cat1_toyota_yaris" / "body.fbx",
     ROOT / "content" / "cars" / "hk_cat1_toyota_yaris" / "hk_cat1_toyota_yaris.kn5"),
    ("prius", "car",
     ROOT / "content" / "cars" / "hk_cat1a_toyota_prius" / "body.fbx",
     ROOT / "content" / "cars" / "hk_cat1a_toyota_prius" / "hk_cat1a_toyota_prius.kn5"),
    ("hiace_mt", "car",
     ROOT / "content" / "cars" / "hk_cat2_toyota_hiace_mt" / "body.fbx",
     ROOT / "content" / "cars" / "hk_cat2_toyota_hiace_mt" / "hk_cat2_toyota_hiace_mt.kn5"),
    ("hiace_at", "car",
     ROOT / "content" / "cars" / "hk_cat2a_toyota_hiace_at" / "body.fbx",
     ROOT / "content" / "cars" / "hk_cat2a_toyota_hiace_at" / "hk_cat2a_toyota_hiace_at.kn5"),
    ("e500_gen1", "car",
     ROOT / "content" / "cars" / "hk_cat17_adl_e500_gen1" / "body.fbx",
     ROOT / "content" / "cars" / "hk_cat17_adl_e500_gen1" / "hk_cat17_adl_e500_gen1.kn5"),
    ("e500_mmc", "car",
     ROOT / "content" / "cars" / "hk_cat17a_adl_e500_mmc" / "body.fbx",
     ROOT / "content" / "cars" / "hk_cat17a_adl_e500_mmc" / "hk_cat17a_adl_e500_mmc.kn5"),
]

TARGET_BY_ID = {t[0]: t for t in TARGETS}


def attach_kseditor():
    """Find ksEditor window and attach UIA wrapper."""
    hwnd = user32.FindWindowW(None, "ksEditor Public")
    if not hwnd:
        return None, None
    import comtypes
    from comtypes.gen import UIAutomationClient
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.uia_element_info import UIAElementInfo
    uia = comtypes.CoCreateInstance(
        UIAutomationClient.CUIAutomation._reg_clsid_,
        interface=UIAutomationClient.IUIAutomation,
        clsctx=comtypes.CLSCTX_INPROC_SERVER,
    )
    udlg = UIAWrapper(UIAElementInfo(uia.ElementFromHandle(hwnd)))
    return hwnd, udlg


def find_item(win, name, ctype="MenuItem", retries=10, delay=1.5):
    for _ in range(retries):
        try:
            for ctrl in win.descendants():
                try:
                    if (ctrl.element_info.control_type == ctype
                            and ctrl.window_text() == name):
                        return ctrl
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(delay)
    return None


def real_click(x, y, wait=2.5):
    user32.SetCursorPos(x, y)
    time.sleep(0.3)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.1)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(wait)


def click_menu_item(dlg, name: str) -> bool:
    item = find_item(dlg, name)
    if item is None:
        return False
    r = item.rectangle()
    real_click(r.left + (r.right - r.left) // 2,
               r.top + (r.bottom - r.top) // 2, 3)
    return True


def find_dialog(title: str, timeout: int = 20):
    desktop = Desktop(backend="win32")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for w in desktop.windows():
                try:
                    if w.class_name() == "#32770" and title in w.window_text():
                        return w
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(1.5)
    return None


def fill_dialog(dialog, path: Path, button_text: str = "Open") -> bool:
    hwnd = dialog.handle
    if not dialog.is_visible():
        user32.ShowWindow(hwnd, 5)
        time.sleep(1)
    edits: list[int] = []
    buttons: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _l):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, buf, 256)
        if buf.value == "Edit":
            edits.append(h)
        elif buf.value == "Button":
            buttons.append(h)
        return True

    user32.EnumChildWindows(hwnd, cb, 0)
    if not edits:
        return False
    user32.SendMessageW(edits[-1], WM_SETTEXT, 0, ctypes.c_wchar_p(str(path)))
    time.sleep(1)
    for bh in buttons:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(bh, buf, 256)
        if button_text in buf.value:
            user32.SendMessageW(bh, BM_CLICK, 0, 0)
            return True
    return False


def convert_one(target: tuple, retries: int = 2) -> bool:
    tid, kind, fbx, kn5 = target
    if not fbx.exists():
        print(f"[SKIP] {tid}: FBX not found: {fbx}")
        return False
    if kn5.exists() and kn5.stat().st_size > 0:
        print(f"[SKIP] {tid}: KN5 already exists: {kn5}")
        return True
    kn5.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, retries + 1):
        proc = None
        try:
            proc = subprocess.Popen([str(KSEDITOR)], cwd=str(KSEDITOR.parent))
            print(f"[CONVERT] {tid} (attempt {attempt}/{retries}): "
                  f"pid {proc.pid}")
            time.sleep(25)

            _, udlg = attach_kseditor()
            if udlg is None:
                raise RuntimeError("ksEditor window not found")

            # File -> Open FBX
            if not click_menu_item(udlg, "File"):
                raise RuntimeError("File menu not found")
            if not click_menu_item(udlg, "Open FBX"):
                raise RuntimeError("Open FBX not found")
            dialog = find_dialog("Open")
            if dialog is None:
                raise RuntimeError("Open dialog not found")
            fill_dialog(dialog, fbx, "Open")
            print(f"  [open] {fbx.name}")
            time.sleep(12)  # FBX load

            # File -> Save KN5 -> Track/Car
            if not click_menu_item(udlg, "File"):
                raise RuntimeError("File menu not found (save)")
            if not click_menu_item(udlg, "Save KN5"):
                raise RuntimeError("Save KN5 not found")
            sub = "Track" if kind == "track" else "Car"
            if not click_menu_item(udlg, sub):
                raise RuntimeError(f"{sub} submenu not found")
            dialog = find_dialog("Save", timeout=15)
            if dialog is None:
                for title in ("Save As", "Export"):
                    dialog = find_dialog(title, timeout=5)
                    if dialog:
                        break
            if dialog is None:
                raise RuntimeError("Save dialog not found")
            fill_dialog(dialog, kn5, "Save")
            print(f"  [save] {kn5.name}")
            time.sleep(8)

            if kn5.exists() and kn5.stat().st_size > 0:
                print(f"[OK] {tid}: {kn5.name} ({kn5.stat().st_size/1024:.0f} KB)")
                return True
            print(f"[FAIL] {tid}: KN5 not created (attempt {attempt})")
        except Exception as e:
            print(f"[ERROR] {tid} (attempt {attempt}): {e}")
        finally:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    time.sleep(1)
                    if proc.poll() is None:
                        proc.kill()
                except Exception:
                    pass
            time.sleep(2)
    return False


def main() -> None:
    args = sys.argv[1:]
    if "--list" in args or "-l" in args:
        for tid, kind, fbx, kn5 in TARGETS:
            state = "OK" if kn5.exists() and kn5.stat().st_size > 0 else "PENDING"
            print(f"  {tid:12s} {kind:5s} {fbx.name:20s} -> {kn5.name} [{state}]")
        return

    wanted = {a for a in args if not a.startswith("--")}
    targets = [t for t in TARGETS if t[0] in wanted] if wanted else TARGETS

    print(f"Converting {len(targets)} file(s)...")
    results = [(t[0], convert_one(t)) for t in targets]
    ok = sum(1 for _, r in results if r)
    print(f"\n[DONE] {ok}/{len(results)} converted successfully")


if __name__ == "__main__":
    main()
