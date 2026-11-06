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


def detect_signal_positions(centre):
    """Return local AC coordinates of OSM traffic-signal road junctions."""
    src = ROOT / 'build' / 'HP1C' / 'source' / f'{centre}_hd_roads.json'
    if not src.exists():
        return []
    with open(src, 'r', encoding='utf-8') as f:
        data = json.load(f)
    ref = (float(data['reference']['lat']), float(data['reference']['lon']))
    lat0, lon0 = ref
    m_lat = 111320.0
    m_lon = 111320.0 * math.cos(math.radians(lat0))
    positions = []
    for el in data.get('elements', []):
        tags = el.get('tags', {})
        if tags.get('junction') != 'traffic_signals':
            continue
        geom = el.get('geometry', [])
        if not geom:
            continue
        # average the way's geometry as the signal location
        xs = [(p['lon'] - lon0) * m_lon for p in geom]
        zs = [-(p['lat'] - lat0) * m_lat for p in geom]
        positions.append([sum(xs) / len(xs), 0.08, sum(zs) / len(zs)])
    return positions


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
    """Build traffic lanes from the whole drivable OSM network.

    Earlier versions chained the AI spline into one path, which covered only
    a fraction of each map (tin_kwong had 1450 roads but 4 lanes). Now every
    OSM way becomes its own pair of lanes, so traffic can use the full
    network and junctions connect them.
    """
    roads = load_osm_roads(centre)
    if not roads:
        raise FileNotFoundError(f"no OSM extract for {centre}")

    min_lane_length = 25.0
    max_segment_gap = 8.0

    def resample(pts, spacing=2.0):
        """Sample a polyline at a fixed spacing."""
        if len(pts) < 2:
            return []
        out = [list(pts[0])]
        carried = 0.0
        for i in range(1, len(pts)):
            a, b = out[-1], pts[i]
            seg = math.hypot(b[0] - a[0], b[2] - a[2])
            if seg < 1e-6:
                continue
            while carried + seg >= spacing:
                t = (spacing - carried) / seg
                nx = a[0] + (b[0] - a[0]) * t
                nz = a[2] + (b[2] - a[2]) * t
                out.append([nx, a[1], nz])
                a = out[-1]
                seg = math.hypot(b[0] - a[0], b[2] - a[2])
                carried = 0.0
                if seg < 1e-6:
                    break
            else:
                carried += seg
        return out

    def split_gaps(points):
        """Split where consecutive samples jump far apart."""
        chunks, current = [], [points[0]] if points else []
        for point in points[1:]:
            prev = current[-1]
            if math.hypot(point[0] - prev[0], point[2] - prev[2]) > max_segment_gap:
                if len(current) >= 3:
                    chunks.append(current)
                current = [point]
            else:
                current.append(point)
        if len(current) >= 3:
            chunks.append(current)
        return chunks

    def offset_polyline(points, offset):
        result = []
        for i, point in enumerate(points):
            previous = points[max(0, i - 1)]
            following = points[min(len(points) - 1, i + 1)]
            tangent_x = following[0] - previous[0]
            tangent_z = following[2] - previous[2]
            length = math.hypot(tangent_x, tangent_z)
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

    def polyline_length(points):
        return sum(
            math.hypot(points[i][0] - points[i - 1][0], points[i][2] - points[i - 1][2])
            for i in range(1, len(points))
        )

    def decimate(points, keep=3):
        """Keep every `keep`-th point plus the last one (curves stay sampled)."""
        if len(points) <= 6 or keep <= 1:
            return points
        out = [points[i] for i in range(0, len(points), keep)]
        if out[-1] is not points[-1]:
            out.append(points[-1])
        return out if len(out) >= 3 else points

    lanes = []
    total_points = 0
    lane_id = 1
    skipped_short = 0
    for road in roads:
        for chunk in split_gaps(resample(road["pts"])):
            if polyline_length(chunk) < min_lane_length:
                skipped_short += 1
                continue
            # Two directions: left offset forward, right offset reversed.
            for suffix, directed in (
                ("A", offset_polyline(chunk, LANE_OFFSET_METERS)),
                ("B", list(reversed(offset_polyline(chunk, -LANE_OFFSET_METERS)))),
            ):
                # Thin out long stretches: keep every 3rd point on straights so
                # traffic.json stays a sane size while curves stay accurate.
                directed = decimate(directed)
                dx = directed[0][0] - directed[-1][0]
                dz = directed[0][2] - directed[-1][2]
                is_loop = math.hypot(dx, dz) <= 5.0
                lanes.append({
                    "name": f"HK {centre} lane {road['id']}{suffix}",
                    "id": lane_id,
                    "loop": is_loop,
                    "role": 3,
                    "priorityOffset": 0,
                    "points": directed,
                    "params": {
                        "allowLaneChanges": False,
                        "allowUTurns": False,
                    },
                })
                total_points += len(directed)
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
    signal_positions = detect_signal_positions(centre)
    for inter in detect_junctions(load_osm_roads(centre), centre):
        ib = inter_aabb(inter['points'])
        n = sum(1 for lb in lane_boxes if aabb_intersect(ib, lb))
        if n >= 2:
            # Tag the junction with a basic traffic-light program if an OSM
            # traffic-signal way is within the junction polygon.
            cx = (inter['points'][0][0] + inter['points'][2][0]) / 2
            cz = (inter['points'][0][2] + inter['points'][2][2]) / 2
            half = (inter['points'][2][0] - inter['points'][0][0]) / 2
            if any((cx - half <= sx <= cx + half and cz - half <= sz <= cz + half)
                   for sx, sy, sz in signal_positions):
                inter['trafficLight'] = {
                    'program': 'Basic',
                    'params': {'duration': 15},
                }
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
