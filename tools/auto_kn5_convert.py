"""Automate ksEditor FBX → KN5 conversion via UI Automation.

Usage (from repo root, on an INTERACTIVE desktop session):
    python tools/auto_kn5_convert.py                 # convert all (maps + cars)
    python tools/auto_kn5_convert.py yaris           # convert one by id
    python tools/auto_kn5_convert.py --list          # list conversion targets

Requires: pywinauto (pip install pywinauto)

VERIFIED (2026-10-13):
- ksEditor is a WinForms app with UIA-accessible menus:
    File -> Open FBX        (opens standard #32770 file dialog)
    File -> Save KN5 -> Track/Car
- UIA `invoke()` works on the top-level "File" menu item.
- Mouse click on "Open FBX" opens the standard Open dialog.
- IMPORTANT: requires an interactive desktop (mouse/keyboard).
  In a headless/remote session without active desktop, mouse APIs fail.

This script uses mouse clicks (most reliable for ksEditor) and handles the
standard file dialogs by typing the path and pressing Enter.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Desktop, mouse

ROOT = Path(__file__).resolve().parents[1]
KSEDITOR = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe")

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


def find_main_window(timeout: int = 30):
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
        time.sleep(1)
    raise RuntimeError("ksEditor main window not found")


def find_menu_item(dlg, name: str, retries: int = 8):
    """Find a MenuItem by name among descendants."""
    for _ in range(retries):
        for ctrl in dlg.descendants():
            try:
                if (ctrl.element_info.control_type == "MenuItem"
                        and ctrl.window_text() == name):
                    return ctrl
            except Exception:
                continue
        time.sleep(1)
    return None


def click_at_center(item) -> None:
    """Mouse-click at an item's screen center."""
    rect = item.rectangle()
    cx = rect.left + (rect.right - rect.left) // 2
    cy = rect.top + (rect.bottom - rect.top) // 2
    mouse.click(coords=(cx, cy))
    time.sleep(2.5)


def open_menu_and_click(dlg, menu_path: list[str]) -> None:
    """Click a menu path using UIA invoke for top menu + mouse for items."""
    # top menu via invoke (works headless)
    top = find_menu_item(dlg, menu_path[0])
    if top is None:
        raise RuntimeError(f"Menu not found: {menu_path[0]}")
    top.invoke()
    time.sleep(2)

    # sub items via mouse click (needs desktop)
    for name in menu_path[1:]:
        item = find_menu_item(dlg, name)
        if item is None:
            raise RuntimeError(f"Menu item not found: {name}")
        click_at_center(item)


def fill_file_dialog(dlg, path: Path) -> None:
    """Type a path into the standard file dialog and press Enter."""
    time.sleep(1.5)
    try:
        dlg.type_keys("^a")
        time.sleep(0.3)
        dlg.type_keys(str(path), with_spaces=True)
        time.sleep(0.3)
        dlg.type_keys("{ENTER}")
    except Exception as e:
        raise RuntimeError(f"Could not fill dialog: {e}")
    time.sleep(2)


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
        time.sleep(2)
        fill_file_dialog(dlg, fbx)
        time.sleep(5)  # wait for FBX load

        # File -> Save KN5 -> Track/Car
        open_menu_and_click(dlg, ["File", "Save KN5",
                                  "Track" if kind == "track" else "Car"])
        time.sleep(2)
        fill_file_dialog(dlg, kn5)
        time.sleep(3)

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
    print("NOTE: requires an interactive desktop session (mouse access).\n")
    results = [(t[0], convert_one(t)) for t in targets]
    ok = sum(1 for _, r in results if r)
    print(f"\n[DONE] {ok}/{len(results)} converted successfully")


if __name__ == "__main__":
    main()
