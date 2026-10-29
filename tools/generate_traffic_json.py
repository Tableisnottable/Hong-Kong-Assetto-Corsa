import struct, json, os, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE_OFFSET_METERS = 1.75

TRACKS = {
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


def read_ai(path: Path):
    raw = path.read_bytes()
    off = 0
    version, count, lap, samples = struct.unpack_from('<4i', raw, off)
    off += 16
    if version != 7:
        raise ValueError(f'{path}: unsupported AI version {version}')
    points = []
    for _ in range(count):
        x, y, z, length, ident = struct.unpack_from('<3ffi', raw, off)
        off += 20
        points.append([x, y, z])
    return points


def load_osm_roads(centre: str):
    """Load drivable road polylines in AC coordinates from the OSM extract."""
    src = ROOT / 'build' / 'HP1C' / 'source' / f'{centre}_hd_roads.json'
    if not src.exists():
        return []
    with open(src, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ref = (float(data['reference']['lat']), float(data['reference']['lon']))
    lat0, lon0 = ref
    m_lat = 111320.0
    m_lon = 111320.0 * math.cos(math.radians(lat0))

    PREFERRED = {"motorway", "trunk", "primary", "secondary", "tertiary",
                 "unclassified", "residential"}
    roads = []
    for el in data.get('elements', []):
        tags = el.get('tags', {})
        if tags.get('highway') not in PREFERRED:
            continue
        geom = el.get('geometry', [])
        if len(geom) < 2:
            continue
        pts = []
        for p in geom:
            x = (p['lon'] - lon0) * m_lon
            z = -(p['lat'] - lat0) * m_lat
            pts.append([x, 0.08, z])
        roads.append({'id': el['id'], 'pts': pts})
    return roads


def detect_junctions(roads, centre='', grid=0.5, min_roads=3, radius=8.0):
    """Find shared endpoints (junctions) and build square polygons for them."""
    # Round endpoints to a coarse grid so near-identical points merge.
    from collections import defaultdict
    counts = defaultdict(list)
    for road in roads:
        pts = road['pts']
        for p in (pts[0], pts[-1]):
            key = (round(p[0] / grid), round(p[2] / grid))
            counts[key].append(p)
    junctions = []
    for key, pts in counts.items():
        if len(pts) < min_roads:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cz = sum(p[2] for p in pts) / len(pts)
        half = radius
        junctions.append({
            'name': f'HK {centre} junction {key[0]}_{key[1]}',
            'id': len(junctions) + 1,
            'points': [
                [cx - half, 0.08, cz - half],
                [cx + half, 0.08, cz - half],
                [cx + half, 0.08, cz + half],
                [cx - half, 0.08, cz + half],
            ],
        })
    return junctions


def make_traffic(track_id: str, centre: str):
    ai_path = ROOT / 'build' / 'HP1C' / centre / 'ai' / 'fast_lane.ai'
    if not ai_path.exists():
        raise FileNotFoundError(ai_path)
    points = read_ai(ai_path)
    # Traffic Planner consumes editor-style lane data. The AI spline is a
    # best-effort chain and can contain jumps between unrelated OSM ways. Split
    # those jumps into independent enter/exit lanes instead of asking Traffic
    # Planner to drive across an artificial 50–100m segment.
    # Offset lanes can add a small amount to a segment gap, so keep the
    # centreline split threshold below the final 10m runtime safety limit.
    max_segment_gap = 8.0
    lanes_points = []
    current = [points[0]] if points else []
    for point in points[1:]:
        previous = current[-1]
        dx = point[0] - previous[0]
        dz = point[2] - previous[2]
        if (dx * dx + dz * dz) ** 0.5 > max_segment_gap:
            if len(current) >= 3:
                lanes_points.append(current)
            current = [point]
        else:
            current.append(point)
    if len(current) >= 3:
        lanes_points.append(current)

    def offset_polyline(points, offset):
        """Offset a local AC x/z polyline while preserving its height."""
        result = []
        for i, point in enumerate(points):
            previous = points[max(0, i - 1)]
            following = points[min(len(points) - 1, i + 1)]
            tangent_x = following[0] - previous[0]
            tangent_z = following[2] - previous[2]
            length = (tangent_x * tangent_x + tangent_z * tangent_z) ** 0.5
            if length < 1e-6:
                result.append(list(point))
                continue
            normal_x = -tangent_z / length
            normal_z = tangent_x / length
            result.append([
                point[0] + normal_x * offset,
                point[1],
                point[2] + normal_z * offset,
            ])
        return result

    lanes = []
    total_points = 0
    lane_id = 1
    for lane_points in lanes_points:
        # Build two separated lanes. The second lane runs in the opposite
        # direction, which prevents traffic cars from sharing one centreline.
        left_points = offset_polyline(lane_points, LANE_OFFSET_METERS)
        right_points = list(reversed(offset_polyline(lane_points, -LANE_OFFSET_METERS)))
        for direction, directed_points in (("A", left_points), ("B", right_points)):
            dx = directed_points[0][0] - directed_points[-1][0]
            dz = directed_points[0][2] - directed_points[-1][2]
            is_loop = (dx * dx + dz * dz) ** 0.5 <= 5.0
            lanes.append({
                'name': f'HK {centre} traffic lane {lane_id}{direction}',
                'id': lane_id,
                'loop': is_loop,
                'role': 3,
                'priorityOffset': 0,
                'points': directed_points,
                'params': {
                    'allowLaneChanges': False,
                    'allowUTurns': False,
                },
            })
            total_points += len(directed_points)
            lane_id += 1

    # Only keep junctions that actually intersect at least two lanes, so the
    # traffic graph can route between lanes at those points.
    def lane_aabb(points):
        return (min(p[0] for p in points), min(p[2] for p in points),
                max(p[0] for p in points), max(p[2] for p in points))

    def inter_aabb(points):
        xs = [p[0] for p in points]
        zs = [p[2] for p in points]
        return (min(xs), min(zs), max(xs), max(zs))

    def aabb_intersect(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    lane_boxes = [lane_aabb(l['points']) for l in lanes]
    useful_intersections = []
    for inter in detect_junctions(load_osm_roads(centre), centre):
        ib = inter_aabb(inter['points'])
        n = sum(1 for lb in lane_boxes if aabb_intersect(ib, lb))
        if n >= 2:
            useful_intersections.append(inter)

    data = {
        'lanes': lanes,
        'intersections': useful_intersections,
        'areas': [],
        'rules': {
            'laneRoles': [
                {'name': 'Parking', 'priority': -8, 'speedLimit': 40},
                {'name': 'Secondary', 'priority': -4, 'speedLimit': 50},
                {'name': 'Main', 'priority': 0, 'speedLimit': 50},
                {'name': 'Highway', 'priority': 4, 'speedLimit': 50},
            ],
        },
    }
    out = ROOT / 'content' / 'tracks' / track_id / 'data' / 'traffic.json'
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return out, total_points, len(lanes)


if __name__ == '__main__':
    targets = sys.argv[1:] or list(TRACKS)
    for track_id in targets:
        if track_id not in TRACKS:
            raise SystemExit(f'Unknown track: {track_id}')
        out, count, lanes = make_traffic(track_id, TRACKS[track_id])
        with open(out, 'r', encoding='utf-8') as f:
            n_inter = len(json.load(f)['intersections'])
        print(f'[OK] {track_id}: {count} points in {lanes} lanes, {n_inter} junctions -> {out}')
