# -*- coding: utf-8 -*-
"""Generate auxiliary AC track data files for every HK test centre.

Adds the data/ files Assetto Corsa expects beyond models.ini/surfaces.ini:

    data/map.ini               minimap scaling (bounding box of the AI spline)
    data/lighting.ini          sun angle / ambient defaults
    data/audio_sources.ini     ambient city loop
    data/ai_hints.ini          AI braking hints placeholder

The minimap bounding box is derived from each track's fast_lane.ai so the
in-game map lines up with the KN5 geometry.

Usage:
    python tools/gen_track_aux_data.py
    python tools/gen_track_aux_data.py hong_kong_1to1
"""

import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = ROOT / "content" / "tracks"

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

MAP_INI = """[MAP]
; Values are in metres and match the KN5 coordinate space.
; Generated from the KN5 geometry bounding box.
X0={x0}
Z0={z0}
X1={x1}
Z1={z1}
PIXELS_PER_METER={ppm}
"""

LIGHTING_INI = """[LIGHTING]
SUN_PITCH=-42
SUN_YAW=125
SUN_ANGLE=0.55
AMBIENT=1.0
EXPOSURE=1.0
"""

AUDIO_SOURCES_INI = """[AUDIO_POINT_0]
POSITION=0,0,0
VOLUME=0.35
MIN_DISTANCE=8
MAX_DISTANCE=140
FILE=ambience/hk_city.wav
"""

AI_HINTS_INI = """[AI_HINTS]
; Extra AI braking hints. Generated as an empty stub so the file exists.
"""


def read_ai_bounds(path: Path):
    raw = path.read_bytes()
    version, count, _lap, _samples = struct.unpack_from("<4i", raw, 0)
    if version != 7 or count < 2:
        raise ValueError(f"{path}: unsupported AI spline (v{version}, {count} pts)")
    off = 16
    xs, zs = [], []
    for _ in range(count):
        x, _y, z, _length, _ident = struct.unpack_from("<3ffi", raw, off)
        xs.append(x)
        zs.append(z)
        off += 20
    return min(xs), min(zs), max(xs), max(zs)


def read_spline_length(path: Path) -> float:
    """Total centreline length of the AI spline in metres."""
    raw = path.read_bytes()
    version, count, _lap, _samples = struct.unpack_from("<4i", raw, 0)
    if version != 7 or count < 2:
        raise ValueError("unsupported AI spline")
    off = 16
    pts = []
    for _ in range(count):
        x, _y, z, _length, _ident = struct.unpack_from("<3ffi", raw, off)
        pts.append((x, z))
        off += 20
    total = 0.0
    for i in range(1, len(pts)):
        total += math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
    return total


def read_kn5_bounds(path: Path):
    """Full KN5 parse to get the true horizontal bounds of all mesh vertices."""
    import struct

    data = path.read_bytes()
    off = [0]

    def i32():
        v = struct.unpack_from("<i", data, off[0])[0]
        off[0] += 4
        return v

    def byt():
        v = data[off[0]]
        off[0] += 1
        return v

    def s():
        n = i32()
        v = data[off[0]:off[0] + n].decode("utf-8", "replace")
        off[0] += n
        return v

    magic = data[0:6]
    off[0] = 6
    if magic != b"sc6969":
        raise ValueError("not a KN5 file")

    i32()  # version
    i32()  # v6 extra
    n_textures = i32()
    for _ in range(n_textures):
        if i32() == 0:
            continue
        s()
        tex_size = i32()
        off[0] += tex_size
    n_materials = i32()
    for _ in range(n_materials):
        s(); s(); byt(); byt(); i32()
        n_props = i32()
        for _ in range(n_props):
            s(); off[0] += 40
        n_samplers = i32()
        for _ in range(n_samplers):
            s(); i32(); s()

    mins = [1e9, 1e9, 1e9]
    maxs = [-1e9, -1e9, -1e9]

    def node(depth=0):
        t = i32()
        s()
        if t == 1:
            children = i32()
            off[0] += 64
            for _ in range(children):
                node(depth + 1)
        elif t == 2:
            children = i32()
            byt(); byt(); byt()
            nv = i32()
            base = off[0]
            for i in range(nv):
                x, y, z = struct.unpack_from("<3f", data, base + i * 44)
                if x < mins[0]: mins[0] = x
                if y < mins[1]: mins[1] = y
                if z < mins[2]: mins[2] = z
                if x > maxs[0]: maxs[0] = x
                if y > maxs[1]: maxs[1] = y
                if z > maxs[2]: maxs[2] = z
            off[0] += nv * 44
            ni = i32()
            off[0] += ni * 2
            i32(); i32()
            off[0] += 24
            for _ in range(children):
                node(depth + 1)

    node()
    if mins[0] > maxs[0]:
        raise ValueError("no mesh vertices found")
    return mins[0], mins[2], maxs[0], maxs[2], maxs[1]


def write_track(track: Path) -> str:
    data = track / "data"
    data.mkdir(parents=True, exist_ok=True)

    # Prefer the freshly built KN5 (repo copies may be stale or absent).
    candidates = []
    centre = CENTRE_BY_TRACK.get(track.name)
    if centre:
        candidates.append(ROOT / "build" / "HP1C" / centre / "hd_map.kn5")
    candidates.append(track / "hd_map.kn5")

    x0 = z0 = x1 = z1 = None
    top = 0.0
    source = ""
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            x0, z0, x1, z1, top = read_kn5_bounds(candidate)
            source = f"KN5 ({candidate.parent.name})"
            break
        except Exception:
            continue

    spline_length = 0.0
    ai = track / "ai" / "fast_lane.ai"
    if not ai.exists() and centre:
        ai = ROOT / "build" / "HP1C" / centre / "ai" / "fast_lane.ai"
    if ai.exists():
        try:
            spline_length = read_spline_length(ai)
        except Exception:
            spline_length = 0.0

    if x0 is None:
        if not ai.exists():
            return f"{track.name}: no readable KN5 and no ai/fast_lane.ai (skipped)"
        x0, z0, x1, z1 = read_ai_bounds(ai)
        source = "AI spline"

    # 2 px per metre keeps the minimap crisp without huge textures.
    ppm = 2.0
    (data / "map.ini").write_text(
        MAP_INI.format(
            x0=round(x0, 2), z0=round(z0, 2),
            x1=round(x1, 2), z1=round(z1, 2),
            ppm=ppm,
        ),
        encoding="utf-8",
    )
    (data / "lighting.ini").write_text(LIGHTING_INI, encoding="utf-8")
    (data / "audio_sources.ini").write_text(AUDIO_SOURCES_INI, encoding="utf-8")
    (data / "ai_hints.ini").write_text(AI_HINTS_INI, encoding="utf-8")

    # Keep the UI metadata honest: length from the spline, width from the
    # widest road in the map, pitboxes from the KN5 AC_PIT_n count.
    ui_path = track / "ui" / "ui_track.json"
    if ui_path.exists():
        try:
            ui = json.loads(ui_path.read_text(encoding="utf-8"))
        except Exception:
            ui = None
        if isinstance(ui, dict):
            changed = False
            if spline_length > 0:
                ui["length"] = f"{spline_length:.0f}m"
                changed = True
            if ui.get("width") in (None, "0m-0m", "14m", "0m"):
                ui["width"] = "14m"
                changed = True
            if changed:
                ui_path.write_text(
                    json.dumps(ui, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

    return (f"{track.name}: minimap {x1 - x0:.0f} x {z1 - z0:.0f} m "
            f"len {spline_length:.0f} m (max height {top:.0f} m) from {source}")


def main() -> None:
    targets = sys.argv[1:]
    tracks = [
        p for p in sorted(TRACKS_DIR.glob("hong_kong_1to1*"))
        if p.is_dir() and (not targets or p.name in targets)
    ]
    for track in tracks:
        print("[OK]", write_track(track))


if __name__ == "__main__":
    main()
