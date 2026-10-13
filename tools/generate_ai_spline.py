"""Generate Assetto Corsa fast_lane.ai (V7 format) from HD map road data.

The AI line follows the OSM road centerlines of a test centre corridor,
sampled every ~2 metres, using the same local coordinate system as the
Blender HD map generator (origin = test centre reference point).

Usage:
    python tools/generate_ai_spline.py                    # tin_kwong_road
    python tools/generate_ai_spline.py texaco_road        # specific centre
    python tools/generate_ai_spline.py --all              # all centres

Output: build/HP1C/<centre>/ai/fast_lane.ai  (V7 binary format)

V7 format (from AssettoServer FastLaneParser):
    int version = 7
    int detailCount
    int LapTime = 0
    int SampleCount = 0
    per point:  float x, y, z | float length | int id
    int extraCount (= detailCount)
    per point:  speed, gas, brake, obsoleteLatG, radius,
                sideLeft, sideRight, camber, direction,
                normal(x,y,z), length, forward(x,y,z), tag, grade
"""

from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Test centre reference points (must match tools/prepare_hd_map.py)
CENTRES = {
    "tin_kwong_road": {"lat": 22.322, "lon": 114.185, "size_km": 2.4},
    "sheung_on_street": {"lat": 22.264, "lon": 114.243, "size_km": 2.4},
    "texaco_road": {"lat": 22.365, "lon": 114.115, "size_km": 3.0},
}

SAMPLE_DISTANCE = 2.0   # metres between AI points
MIN_ROAD_LEN = 30.0     # skip roads shorter than this
MAX_SPEED = 50.0        # km/h default urban speed


def local_xy(lat: float, lon: float, ref: tuple[float, float]) -> tuple[float, float]:
    lat0, lon0 = ref
    m_lat = 111_320.0
    m_lon = 111_320.0 * math.cos(math.radians(lat0))
    return ((lon - lon0) * m_lon, (lat - lat0) * m_lat)


def sample_centreline(pts: list[tuple[float, float, float]],
                      dist: float = SAMPLE_DISTANCE) -> list[tuple[float, float, float]]:
    """Sample a polyline at fixed spacing, returning (x, y, z) points."""
    if len(pts) < 2:
        return []
    result: list[tuple[float, float, float]] = [pts[0]]
    travelled = 0.0
    i = 1
    while i < len(pts):
        a = result[-1]
        b = pts[i]
        seg = math.dist(a[:2], b[:2])
        if seg < 1e-6:
            i += 1
            continue
        needed = dist - travelled
        if seg >= needed:
            t = needed / seg
            nx = a[0] + (b[0] - a[0]) * t
            ny = a[1] + (b[1] - a[1]) * t
            nz = a[2] + (b[2] - a[2]) * t
            result.append((nx, ny, nz))
            travelled = 0.0
            # continue from the interpolated point
            pts = [*pts[:i], (nx, ny, nz), *pts[i:]]
            i += 1
        else:
            travelled += seg
            result.append(b)
            i += 1
    return result


def heading_between(a: tuple, b: tuple) -> float:
    """Yaw angle in radians (AC uses XZ plane, Y up)."""
    return math.atan2(b[0] - a[0], b[2] - a[2])


def generate_for_centre(centre_id: str) -> Path:
    src = ROOT / "build" / "HP1C" / "source" / f"{centre_id}_hd_roads.json"
    if not src.exists():
        raise SystemExit(f"Extract not found: {src}\n"
                         f"Run: python tools/prepare_hd_map.py {centre_id}")

    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    ref = (float(data["reference"]["lat"]), float(data["reference"]["lon"]))
    elements = data.get("elements", [])

    # Build one long spline by chaining drivable roads (best-effort)
    # Prefer primary/secondary/tertiary/residential; skip footways/services
    PREFERRED = {"motorway", "trunk", "primary", "secondary", "tertiary",
                 "unclassified", "residential"}
    roads = []
    for el in elements:
        tags = el.get("tags", {})
        hw = tags.get("highway", "")
        if hw not in PREFERRED:
            continue
        geom = el.get("geometry", [])
        if len(geom) < 2:
            continue
        pts = [(*local_xy(p["lat"], p["lon"], ref), 0.0) for p in geom]
        sampled = sample_centreline(pts)
        if len(sampled) >= 2:
            roads.append({"id": el["id"], "hw": hw, "pts": sampled})

    roads.sort(key=lambda r: -len(r["pts"]))
    print(f"[{centre_id}] {len(roads)} drivable roads, "
          f"{sum(len(r['pts']) for r in roads)} points total")

    # Chain roads into a single spline: greedy nearest-neighbour join
    used = [False] * len(roads)
    chain: list[tuple[float, float, float]] = []
    order: list[int] = []

    current = -1
    while True:
        best = -1
        best_d = float("inf")
        for i, r in enumerate(roads):
            if used[i]:
                continue
            if chain:
                tail = chain[-1]
                head = r["pts"][0]
                d = math.dist(tail[:2], head[:2])
            else:
                d = 0.0
            if d < best_d:
                best_d = d
                best = i
        if best < 0:
            break
        used[best] = True
        order.append(best)
        if chain and best_d > 50:
            # gap too big - insert a connecting straight segment
            chain.extend(roads[best]["pts"])
        else:
            chain.extend(roads[best]["pts"])

    if len(chain) < 10:
        raise SystemExit(f"[{centre_id}] Too few points ({len(chain)})")

    # Downsample to ~2m if needed
    final: list[tuple[float, float, float]] = []
    for i, p in enumerate(chain):
        if i == 0:
            final.append(p)
            continue
        d = math.dist(final[-1][:2], p[:2])
        if d >= SAMPLE_DISTANCE * 0.5:
            final.append(p)
    print(f"[{centre_id}] chained spline: {len(final)} points")

    return write_v7(centre_id, final)


def write_v7(centre_id: str, points: list[tuple[float, float, float]]) -> Path:
    out_dir = ROOT / "build" / "HP1C" / centre_id / "ai"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "fast_lane.ai"

    n = len(points)
    buf = bytearray()
    buf += struct.pack("<4i", 7, n, 0, 0)

    # main points
    for i, (x, y, z) in enumerate(points):
        nxt = points[i + 1] if i + 1 < n else points[0]
        length = math.dist((x, y, z), nxt)
        buf += struct.pack("<3f", x, y, z)
        buf += struct.pack("<f", length)
        buf += struct.pack("<I", i)

    # extra points
    buf += struct.pack("<i", n)
    for i, (x, y, z) in enumerate(points):
        nxt = points[i + 1] if i + 1 < n else points[0]
        h = heading_between((x, y, z), nxt)
        fwd = (math.sin(h), 0.0, math.cos(h))
        length = math.dist((x, y, z), nxt)
        # speed(km/h), gas, brake, latg, radius, sideL, sideR, camber, direction
        buf += struct.pack("<9f", MAX_SPEED, 1.0, 0.0, 0.0, 500.0,
                           1.75, 1.75, 0.0, 1.0)
        # normal
        buf += struct.pack("<3f", 0.0, 1.0, 0.0)
        # length
        buf += struct.pack("<f", length)
        # forward vector
        buf += struct.pack("<3f", *fwd)
        # tag, grade
        buf += struct.pack("<2f", 0.0, 0.0)

    out.write_bytes(buf)
    print(f"[{centre_id}] WROTE {out} ({len(buf)} bytes, {n} points)")
    return out


def main() -> None:
    args = sys.argv[1:]
    centres = list(CENTRES.keys())
    if args and "--all" not in args:
        centres = [a for a in args if a in CENTRES]
    for c in centres:
        try:
            generate_for_centre(c)
        except SystemExit as e:
            print(e)
    print("[DONE]")


if __name__ == "__main__":
    main()
