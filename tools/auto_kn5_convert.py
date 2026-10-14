"""Automate ksEditor FBX → KN5 conversion via UI Automation.

Usage (from repo root, on an INTERACTIVE desktop session):
    python tools/auto_kn5_convert.py                 # convert all (maps + cars)
    python tools/auto_kn5_convert.py yaris           # convert one by id
    python tools/auto_kn5_convert.py --list          # list conversion targets

Requires: pywinauto (pip install pywinauto)

VERIFIED (2026-10-14):
- ksEditor is a WinForms app with UIA-accessible menus:
    File -> Open FBX        (opens standard #32770 'Open' dialog)
    File -> Save KN5 -> Track/Car
- UIA `invoke()` works on the top-level "File" menu item.
- The Open dialog can be filled via Win32 SendMessage (works even in
  non-foreground sessions): find Edit control, set path, click '&Open'.
- This script uses that proven approach for full automation.
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


def find_main_window(timeout: int = 40):
    """Find the ksEditor main window via UIA Desktop."""
    desktop = Desktop(backend="uia")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for w in desktop.windows():
                try:
                    if w.window_text() == "ksEditor Public":
                        return w
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("ksEditor main window not found")


def find_menu_item(dlg, name: str, retries: int = 10, delay: float = 1.5):
    """Find a MenuItem by name among descendants."""
    for _ in range(retries):
        try:
            for ctrl in dlg.descendants():
                try:
                    if (ctrl.element_info.control_type == "MenuItem"
                            and ctrl.window_text() == name):
                        return ctrl
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(delay)
    return None


def find_dialog(title: str, timeout: int = 20):
    """Find a #32770 dialog by title (win32 backend)."""
    desktop = Desktop(backend="win32")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for w in desktop.windows():
                try:
                    if w.class_name() == "#32770" and w.window_text() == title:
                        return w
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(1)
    return None


def _child_windows(parent: int, cls: str) -> list[int]:
    result: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _lparam):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        if buf.value == cls:
            result.append(hwnd)
        return True

    user32.EnumChildWindows(parent, cb, 0)
    return result


def fill_open_dialog(dialog, path: Path) -> bool:
    """Fill the standard Open dialog via Win32 SendMessage."""
    hwnd = dialog.handle
    edits = _child_windows(hwnd, "Edit")
    buttons = _child_windows(hwnd, "Button")
    if not edits:
        return False

    # Set the filename (usually last Edit = filename field)
    user32.SendMessageW(edits[-1], WM_SETTEXT, 0, ctypes.c_wchar_p(str(path)))
    time.sleep(1)

    # Click the Open button
    for bh in buttons:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(bh, buf, 256)
        if "Open" in buf.value or "開啟" in buf.value:
            user32.SendMessageW(bh, BM_CLICK, 0, 0)
            return True
    # Fallback: press Enter on the dialog
    user32.SendMessageW(hwnd, 0x0100, 0x0D, 0)  # WM_KEYDOWN Enter
    user32.SendMessageW(hwnd, 0x0101, 0x0D, 0)  # WM_KEYUP Enter
    return True


def open_menu_and_click(dlg, menu_path: list[str]) -> None:
    """Open a menu path via UIA invoke."""
    top = find_menu_item(dlg, menu_path[0])
    if top is None:
        raise RuntimeError(f"Menu not found: {menu_path[0]}")
    top.invoke()
    time.sleep(2.5)
    for name in menu_path[1:]:
        item = find_menu_item(dlg, name)
        if item is None:
            raise RuntimeError(f"Menu item not found: {name}")
        try:
            item.invoke()
        except Exception:
            # Some items don't support invoke; click via coordinates as fallback
            rect = item.rectangle()
            cx = rect.left + (rect.right - rect.left) // 2
            cy = rect.top + (rect.bottom - rect.top) // 2
            ctypes.windll.user32.SetCursorPos(cx, cy)
            ctypes.windll.user32.mouse_event(0x02, 0, 0, 0, 0)  # left down
            ctypes.windll.user32.mouse_event(0x04, 0, 0, 0, 0)  # left up
        time.sleep(2.5)


def convert_one(target: tuple) -> bool:
    tid, kind, fbx, kn5 = target
    if not fbx.exists():
        print(f"[SKIP] {tid}: FBX not found: {fbx}")
        return False
    if kn5.exists() and kn5.stat().st_size > 0:
        print(f"[SKIP] {tid}: KN5 already exists: {kn5}")
        return True
    kn5.parent.mkdir(parents=True, exist_ok=True)

    proc = None
    try:
        proc = subprocess.Popen([str(KSEDITOR)], cwd=str(KSEDITOR.parent))
        print(f"[CONVERT] {tid}: launched ksEditor (pid {proc.pid})")
        dlg = find_main_window()
        time.sleep(3)

        # File -> Open FBX
        open_menu_and_click(dlg, ["File", "Open FBX"])
        dialog = find_dialog("Open")
        if dialog is None:
            raise RuntimeError("Open dialog not found")
        fill_open_dialog(dialog, fbx)
        print(f"  [open] {fbx.name}")
        time.sleep(8)  # wait for FBX load

        # File -> Save KN5 -> Track/Car
        open_menu_and_click(dlg, ["File", "Save KN5",
                                  "Track" if kind == "track" else "Car"])
        dialog = find_dialog("Save")
        if dialog is None:
            # Some versions use "Save As" or "Export"
            for title in ("Save", "Save As", "Export"):
                dialog = find_dialog(title, timeout=5)
                if dialog:
                    break
        if dialog is None:
            raise RuntimeError("Save dialog not found")
        fill_open_dialog(dialog, kn5)
        print(f"  [save] {kn5.name}")
        time.sleep(5)

        if kn5.exists() and kn5.stat().st_size > 0:
            print(f"[OK] {tid}: {kn5.name} ({kn5.stat().st_size/1024:.0f} KB)")
            return True
        print(f"[FAIL] {tid}: KN5 not created")
        return False
    except Exception as e:
        print(f"[ERROR] {tid}: {e}")
        return False
    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    proc.kill()
            except Exception:
                pass


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
