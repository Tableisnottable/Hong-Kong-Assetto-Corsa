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
    "happy_valley": {"lat": 22.269, "lon": 114.186, "size_km": 2.0},
    "so_kun_po": {"lat": 22.273, "lon": 114.192, "size_km": 2.0},
    "shek_am": {"lat": 22.369, "lon": 114.138, "size_km": 2.0},
    "yau_tong": {"lat": 22.296, "lon": 114.235, "size_km": 2.0},
    "chung_ngai_street": {"lat": 22.3175, "lon": 114.1745, "size_km": 2.0},
    "pui_ching_road": {"lat": 22.3179742, "lon": 114.1773149, "size_km": 2.0},
    "wing_hau_street": {"lat": 22.3155, "lon": 114.1885, "size_km": 2.0},
    "ap_lei_chau": {"lat": 22.2399354, "lon": 114.1545244, "size_km": 2.0},
    "yuen_long": {"lat": 22.4623971, "lon": 114.0379722, "size_km": 2.5},
    "sha_tin": {"lat": 22.3887506, "lon": 114.2033455, "size_km": 2.0},
}

SAMPLE_DISTANCE = 2.0   # metres between AI points
MIN_ROAD_LEN = 30.0     # skip roads shorter than this
MAX_SPEED = 50.0        # km/h default urban speed
MIN_SPEED = 15.0        # km/h minimum speed for tight corners
SPEED_LIMITS = {        # km/h by road type (from OSM tags)
    "motorway": 80,
    "trunk": 70,
    "primary": 60,
    "secondary": 50,
    "tertiary": 40,
    "residential": 30,
    "service": 20,
    "default": 40,
}


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
    used = [False] * len(roads)

    # Start from the longest road
    start = max(range(len(roads)), key=lambda i: len(roads[i]["pts"]))
    used[start] = True
    order.append(start)
    chain.extend(roads[start]["pts"])

    # Greedily chain nearby roads (max 100m gap)
    MAX_GAP = 100.0
    while True:
        best = -1
        best_d = float("inf")
        tail = chain[-1]
        
        for i, r in enumerate(roads):
            if used[i]:
                continue
            # Check both endpoints
            head_d = math.dist(tail[:2], r["pts"][0][:2])
            tail_d = math.dist(tail[:2], r["pts"][-1][:2])
            d = min(head_d, tail_d)
            if d < best_d:
                best_d = d
                best = i
                best_reversed = tail_d < head_d
        
        if best < 0 or best_d > MAX_GAP:
            break
        
        used[best] = True
        order.append(best)
        
        pts = roads[best]["pts"]
        if best_reversed:
            pts = pts[::-1]  # Reverse to connect tail-to-tail
        chain.extend(pts)

    # If chain is too short, add more roads with larger gaps
    if len(chain) < 100:
        print(f"  [WARN] Short chain ({len(chain)} pts), extending with MAX_GAP=100m")
        MAX_GAP = 100.0
        while True:
            best = -1
            best_d = float("inf")
            tail = chain[-1]
            
            for i, r in enumerate(roads):
                if used[i]:
                    continue
                head_d = math.dist(tail[:2], r["pts"][0][:2])
                tail_d = math.dist(tail[:2], r["pts"][-1][:2])
                d = min(head_d, tail_d)
                if d < best_d:
                    best_d = d
                    best = i
                    best_reversed = tail_d < head_d
            
            if best < 0 or best_d > MAX_GAP:
                break
            
            used[best] = True
            order.append(best)
            
            pts = roads[best]["pts"]
            if best_reversed:
                pts = pts[::-1]
            chain.extend(pts)

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
    
    # Calculate curvature and dynamic speed for each point
    speeds, radii = calculate_dynamic_speeds(points)
    
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
        
        speed = speeds[i]
        radius = radii[i]
        
        # Calculate gas/brake based on speed changes
        if i > 0:
            prev_speed = speeds[i-1]
            if speed < prev_speed - 2.0:  # Decelerating
                gas = 0.0
                brake = min(1.0, (prev_speed - speed) / 10.0)
            elif speed > prev_speed + 2.0:  # Accelerating
                gas = min(1.0, (speed - prev_speed) / 10.0)
                brake = 0.0
            else:  # Constant speed
                gas = 0.7
                brake = 0.0
        else:
            gas = 0.5
            brake = 0.0
        
        # speed(km/h), gas, brake, latg, radius, sideL, sideR, camber, direction
        buf += struct.pack("<9f", speed, gas, brake, 0.0, radius,
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
    print(f"  Speed range: {min(speeds):.1f} - {max(speeds):.1f} km/h")
    print(f"  Radius range: {min(radii):.1f} - {max(radii):.1f} m")


def calculate_dynamic_speeds(points: list[tuple[float, float, float]]) -> tuple[list[float], list[float]]:
    """Calculate speed and radius for each point based on curvature."""
    n = len(points)
    speeds = [MAX_SPEED] * n
    radii = [500.0] * n  # Default large radius (straight)
    
    # Calculate radius using 3-point circumcircle
    window = 5  # Look ahead/behind 5 points (10m at 2m spacing)
    
    for i in range(n):
        # Get points for curvature calculation
        i0 = max(0, i - window)
        i1 = i
        i2 = min(n - 1, i + window)
        
        if i0 == i1 or i1 == i2:
            continue
            
        p0 = points[i0]
        p1 = points[i1]
        p2 = points[i2]
        
        # Calculate circumcircle radius
        radius = circumradius(p0, p1, p2)
        radii[i] = radius
        
        # Speed based on radius (v = sqrt(mu * g * r))
        # mu = 0.4 (conservative for urban), g = 9.81
        max_corner_speed = math.sqrt(0.4 * 9.81 * radius) * 3.6  # Convert to km/h
        
        # Apply speed limit and corner speed
        speeds[i] = min(MAX_SPEED, max(MIN_SPEED, max_corner_speed))
    
    # Smooth speeds (avoid sudden changes)
    smoothed = speeds.copy()
    for i in range(1, n - 1):
        smoothed[i] = (speeds[i-1] + speeds[i] * 2 + speeds[i+1]) / 4.0
    
    # Ensure acceleration/deceleration limits (max 3 m/s²)
    for i in range(1, n):
        max_delta = 3.0 * (points[i][0] - points[i-1][0] if i > 0 else 2.0) / 3.6
        # Simplified: limit change to 5 km/h per point
        if smoothed[i] > smoothed[i-1] + 5.0:
            smoothed[i] = smoothed[i-1] + 5.0
        elif smoothed[i] < smoothed[i-1] - 8.0:  # Allow harder braking
            smoothed[i] = smoothed[i-1] - 8.0
    
    return smoothed, radii


def circumradius(p0, p1, p2) -> float:
    """Calculate circumradius of triangle formed by 3 points."""
    ax, ay = p0[0], p0[1]  # Use x,y (2D plane, z is height=0)
    bx, by = p1[0], p1[1]
    cx, cy = p2[0], p2[1]
    
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-6:
        return 500.0  # Collinear points = straight
    
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    
    radius = math.sqrt((ax - ux)**2 + (ay - uy)**2)
    return min(radius, 1000.0)  # Cap at 1000m
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
