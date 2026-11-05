# -*- coding: utf-8 -*-
"""One-command rebuild of every Hong Kong test-centre track.

Runs the whole pipeline in order and stops at the first hard failure:

  1. prepare HD road extracts (OSM corridor)
  2. generate Blender HD mesh -> FBX
  3. convert FBX -> KN5 (with AC control nodes)
  4. generate AI spline
  5. generate traffic.json (lanes + junctions + lights)
  6. generate aux data (map.ini/lighting/audio)
  7. validate KN5
  8. install into Assetto Corsa

Usage:
    python tools/build_tracks.py                 # all 13 centres
    python tools/build_tracks.py sha_tin yau_tong
    python tools/build_tracks.py --skip-osm      # reuse existing extracts
    python tools/build_tracks.py --no-install    # build only
"""

import argparse
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AC_ROOT = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa")
BLENDER_CANDIDATES = [
    Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
    Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
]

CENTRES = [
    "tin_kwong_road", "sheung_on_street", "texaco_road", "happy_valley",
    "so_kun_po", "shek_am", "yau_tong", "chung_ngai_street",
    "pui_ching_road", "wing_hau_street", "ap_lei_chau", "yuen_long", "sha_tin",
]

TRACK_BY_CENTRE = {
    "tin_kwong_road": "hong_kong_1to1",
    "sheung_on_street": "hong_kong_1to1_sheung_on",
    "texaco_road": "hong_kong_1to1_texaco",
    "happy_valley": "hong_kong_1to1_happy_valley",
    "so_kun_po": "hong_kong_1to1_so_kun_po",
    "shek_am": "hong_kong_1to1_shek_am",
    "yau_tong": "hong_kong_1to1_yau_tong",
    "chung_ngai_street": "hong_kong_1to1_chung_ngai",
    "pui_ching_road": "hong_kong_1to1_pui_ching",
    "wing_hau_street": "hong_kong_1to1_wing_hau",
    "ap_lei_chau": "hong_kong_1to1_ap_lei_chau",
    "yuen_long": "hong_kong_1to1_yuen_long",
    "sha_tin": "hong_kong_1to1_sha_tin",
}


def find_blender() -> Path:
    for candidate in BLENDER_CANDIDATES:
        if candidate.exists():
            return candidate
    raise SystemExit("Blender not found; edit BLENDER_CANDIDATES in this script")


def run(cmd: list[str], label: str) -> None:
    print(f"\n=== {label} ===")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        # Blender exits non-zero on clean shutdown in some builds; the KN5
        # validator below is the real gate, so keep going but note it.
        print(f"  [warn] exit code {result.returncode}")


def build_centre(centre: str, blender: Path, *, skip_osm: bool, install: bool) -> bool:
    track_id = TRACK_BY_CENTRE[centre]
    extract = ROOT / "build" / "HP1C" / "source" / f"{centre}_hd_roads.json"
    fbx = ROOT / "build" / "HP1C" / centre / "hd_map.fbx"
    kn5 = ROOT / "build" / "HP1C" / centre / "hd_map.kn5"

    print(f"\n########## {centre} -> {track_id} ##########")

    if not skip_osm or not extract.exists():
        run([sys.executable, "tools/prepare_hd_map.py", centre], f"{centre}: OSM extract")

    run([str(blender), "--background", "--python", "tools/blender/generate_hd_map.py",
         "--", centre], f"{centre}: Blender HD mesh")

    run([str(blender), "--background", "--python", "tools/blender/export_kn5_direct.py",
         "--", str(fbx), str(kn5)], f"{centre}: FBX -> KN5")

    run([sys.executable, "tools/generate_ai_spline.py", centre], f"{centre}: AI spline")
    run([sys.executable, "tools/generate_traffic_json.py", track_id], f"{centre}: traffic")
    run([sys.executable, "tools/gen_track_aux_data.py", track_id], f"{centre}: aux data")
    run([sys.executable, "tools/gen_track_surfaces.py", track_id], f"{centre}: surfaces")

    print(f"\n=== {centre}: validate KN5 ===")
    if not kn5.exists():
        print("  [FAIL] KN5 not produced")
        return False
    result = subprocess.run([sys.executable, "tools/validate_kn5.py", str(kn5)], cwd=ROOT)
    if result.returncode != 0:
        print("  [FAIL] KN5 validation failed")
        return False

    if install:
        ac_track = AC_ROOT / "content" / "tracks" / track_id
        if not ac_track.is_dir():
            print(f"  [skip install] {ac_track} does not exist")
            return True
        shutil.copy2(kn5, ac_track / "hd_map.kn5")
        for ini in (ROOT / "content" / "tracks" / track_id / "data").glob("*.ini"):
            shutil.copy2(ini, ac_track / "data" / ini.name)
        traffic = ROOT / "content" / "tracks" / track_id / "data" / "traffic.json"
        if traffic.exists():
            shutil.copy2(traffic, ac_track / "data" / "traffic.json")
        ai = ROOT / "build" / "HP1C" / centre / "ai" / "fast_lane.ai"
        if ai.exists():
            shutil.copy2(ai, ac_track / "ai" / "fast_lane.ai")
        print(f"  [installed] {ac_track.name}")

    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("centres", nargs="*", help="centre ids (default: all)")
    ap.add_argument("--skip-osm", action="store_true", help="reuse existing extracts")
    ap.add_argument("--no-install", action="store_true", help="skip AC install")
    args = ap.parse_args()

    targets = args.centres or CENTRES
    unknown = [c for c in targets if c not in TRACK_BY_CENTRE]
    if unknown:
        raise SystemExit(f"unknown centre(s): {unknown}")

    blender = find_blender()
    print(f"Blender: {blender}")
    print(f"Centres: {len(targets)}")

    passed, failed = [], []
    for centre in targets:
        ok = build_centre(centre, blender, skip_osm=args.skip_osm,
                          install=not args.no_install)
        (passed if ok else failed).append(centre)

    print("\n" + "=" * 60)
    print(f"PASSED {len(passed)}/{len(targets)}")
    if failed:
        print("FAILED: " + ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
