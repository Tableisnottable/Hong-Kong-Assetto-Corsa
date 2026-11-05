# -*- coding: utf-8 -*-
"""Generate the remaining AC track data files from each track's AI spline.

Adds what a real AC track ships beyond models/surfaces/map/lighting:

    data/cameras.ini   TV camera set anchored on the track (3 shots + a
                       chase-style wide), so replay/TV modes have framing
    data/groove.ini    rubbered-in racing line mesh hints (groove count)
    data/crew.ini      pit crew side
    data/overlays.ini  start/finish light positions (used by some apps)

Camera positions are derived from the spline so each centre gets sensible
framing instead of the AC default floating camera.

Usage:
    python tools/gen_track_cameras.py
    python tools/gen_track_cameras.py hong_kong_1to1
"""

import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ROOT / "content" / "tracks"

CENTRE_BY_TRACK = {
    "hong_kong_1to1": "tin_kwong_road",
    "hong_kong_1to1_sheung_on": "sheung_on_street",
    "hong_kong_1to1_texaco": "texaco_road",
    "hong_kong_1to1_happy_valley": "happy_valley",
    "hong_kong_1to1_so_kun_po": "so_kun_po",
    "hong_kong_1to1_shek_am": "shek_am",
    "hong_kong_1to1_yau_tong": "yau_tong",
    "hong_kong_1to1_chung_ngai": "chung_ngai_street",
    "hong_kong_1to1_pui_ching": "pui_ching_road",
    "hong_kong_1to1_wing_hau": "wing_hau_street",
    "hong_kong_1to1_ap_lei_chau": "ap_lei_chau",
    "hong_kong_1to1_yuen_long": "yuen_long",
    "hong_kong_1to1_sha_tin": "sha_tin",
}


def read_spline(path: Path):
    raw = path.read_bytes()
    version, count, _lap, _samples = struct.unpack_from("<4i", raw, 0)
    if version != 7 or count < 8:
        raise ValueError(f"{path}: unsupported AI spline")
    points = []
    off = 16
    for _ in range(count):
        x, y, z, _length, _ident = struct.unpack_from("<3ffi", raw, off)
        points.append((x, y, z))
        off += 20
    return points


def fmt(values) -> str:
    return " ,".join(f"{v:.2f}" for v in values)


def camera_block(index: int, name: str, pos, forward, *, fov_min=8,
                 fov_max=60, near=1.0, far=12000) -> str:
    return (
        f"[CAMERA_{index}]\n"
        f"NAME={name}\n"
        f"POSITION={fmt(pos)}\n"
        f"FORWARD={fmt(forward)}\n"
        "UP=0 ,1 ,0\n"
        f"MIN_FOV={fov_min}\n"
        f"MAX_FOV={fov_max}\n"
        "IN_POINT=-1\n"
        "OUT_POINT=-1\n"
        "SHADOW_SPLIT0=120\n"
        "SHADOW_SPLIT1=250\n"
        "SHADOW_SPLIT2=600\n"
        f"NEAR_PLANE={near}\n"
        f"FAR_PLANE={far}\n"
        "MIN_EXPOSURE=0.35\n"
        "MAX_EXPOSURE=0.55\n"
        "DOF_FACTOR=0\n"
        "DOF_RANGE=10000\n"
        "DOF_FOCUS=0\n"
        "DOF_MANUAL=0\n"
        "SPLINE=\n"
        "SPLINE_ROTATION=0\n"
        "FOV_GAMMA=1\n"
        "SPLINE_ANIMATION_LENGTH=15\n"
        "IS_FIXED=0\n"
    )


def build_cameras(points) -> str:
    n = len(points)

    def at(frac):
        return points[int(frac * (n - 1)) % n]

    def heading(a, b):
        dx, dz = b[0] - a[0], b[2] - a[2]
        ln = math.hypot(dx, dz) or 1.0
        return dx / ln, dz / ln

    blocks = []

    # 1. Elevated wide shot looking back along the road (TV-style).
    p = at(0.05)
    q = at(0.10)
    hx, hz = heading(p, q)
    blocks.append(camera_block(
        0, "TV Wide",
        (p[0] - hx * 18.0, 9.5, p[2] - hz * 18.0),
        (hx, -0.28, hz),
        fov_min=20, fov_max=45,
    ))

    # 2. Low roadside camera at a bend, looking across the carriageway.
    p = at(0.45)
    q = at(0.50)
    hx, hz = heading(p, q)
    # Perpendicular offset puts the camera beside the road.
    blocks.append(camera_block(
        1, "TV Trackside",
        (p[0] - hz * 11.0, 2.4, p[2] + hx * 11.0),
        (hz, -0.10, -hx),
        fov_min=12, fov_max=55,
    ))

    # 3. Chase-style trailing camera.
    p = at(0.70)
    q = at(0.75)
    hx, hz = heading(p, q)
    blocks.append(camera_block(
        2, "TV Chase",
        (p[0] - hx * 8.0, 3.2, p[2] - hz * 8.0),
        (hx, -0.12, hz),
        fov_min=30, fov_max=65, near=0.5,
    ))

    # 4. Overhead anchor for the start area.
    p = at(0.0)
    blocks.append(camera_block(
        3, "TV Aerial",
        (p[0], 55.0, p[2]),
        (0.0, -1.0, 0.001),
        fov_min=35, fov_max=70, near=2.0, far=20000,
    ))

    header = (
        "[HEADER]\n"
        "VERSION=3\n"
        f"CAMERA_COUNT={len(blocks)}\n"
        "SET_NAME=HK TV\n\n"
    )
    return header + "\n".join(blocks)


def build_groove(track_m: float) -> str:
    # AC uses the groove mesh from the KN5; the ini only counts available
    # groove levels. Setting 2 gives the tyre-rubber darkening level.
    return "[HEADER]\nGROOVES_NUMBER=2\n"


GROOVE_LEVEL = "[GROOVE_0]\nSTART=0\nEND=1\n"

CREW_INI = "[HEADER]\nSIDE=-1 ; 1 = left , -1 = right\n"


def build_overlays(points) -> str:
    # Start/finish light bar above the start line.
    p = points[0]
    lines = ["[MAIN]", "OVERLAYS_COUNT=1", "", "[CHECKPOINT_0]"]
    lines.append(f"WORLD_POSITION={fmt(p)}")
    lines.append("OFFSET=0 ,3.2 ,0")
    lines.append("WIDTH=14")
    lines.append("HEIGHT=1.2")
    lines.append("ORIENTATION=0 ,0 ,0")
    return "\n".join(lines) + "\n"


def main() -> None:
    targets = sys.argv[1:]
    for track in sorted(TRACKS.glob("hong_kong_1to1*")):
        if not track.is_dir() or (targets and track.name not in targets):
            continue
        centre = CENTRE_BY_TRACK[track.name]
        spline = ROOT / "build" / "HP1C" / centre / "ai" / "fast_lane.ai"
        repo_ai = track / "ai" / "fast_lane.ai"
        source = spline if spline.exists() else repo_ai
        if not source.exists():
            print(f"[skip] {track.name}: no AI spline")
            continue
        points = read_spline(source)
        data = track / "data"
        data.mkdir(parents=True, exist_ok=True)
        (data / "cameras.ini").write_text(build_cameras(points), encoding="utf-8")
        (data / "groove.ini").write_text(build_groove(0.0), encoding="utf-8")
        (data / "crew.ini").write_text(CREW_INI, encoding="utf-8")
        (data / "overlays.ini").write_text(build_overlays(points), encoding="utf-8")
        print(f"[OK] {track.name}: cameras(4) groove crew overlays")


if __name__ == "__main__":
    main()
