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

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS_DIR = ROOT / "content" / "tracks"

MAP_INI = """[MAP]
; Values are in metres and match the KN5 coordinate space.
; Generated from the AI spline bounding box.
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


def write_track(track: Path) -> str:
    ai = track / "ai" / "fast_lane.ai"
    data = track / "data"
    data.mkdir(parents=True, exist_ok=True)
    if not ai.exists():
        return f"{track.name}: no ai/fast_lane.ai (skipped)"

    x0, z0, x1, z1 = read_ai_bounds(ai)
    # 2 px per metre keeps the minimap crisp without huge textures.
    ppm = 2.0
    (data / "map.ini").write_text(
        MAP_INI.format(
            x0=round(x0, 2),
            z0=round(z0, 2),
            x1=round(x1, 2),
            z1=round(z1, 2),
            ppm=ppm,
        ),
        encoding="utf-8",
    )
    (data / "lighting.ini").write_text(LIGHTING_INI, encoding="utf-8")
    (data / "audio_sources.ini").write_text(AUDIO_SOURCES_INI, encoding="utf-8")
    (data / "ai_hints.ini").write_text(AI_HINTS_INI, encoding="utf-8")
    span_x = x1 - x0
    span_z = z1 - z0
    return f"{track.name}: map.ini ({span_x:.0f} x {span_z:.0f} m)"


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
