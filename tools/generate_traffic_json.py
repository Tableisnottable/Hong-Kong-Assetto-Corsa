import struct, json, os, sys
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

    data = {
        'lanes': lanes,
        'intersections': [],
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
        print(f'[OK] {track_id}: {count} points in {lanes} lanes -> {out}')
