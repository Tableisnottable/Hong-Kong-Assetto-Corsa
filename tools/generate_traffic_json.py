import struct, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    # Traffic Planner consumes editor-style lane data. Keep the loop in the
    # same local AC coordinates as the KN5/AI spline, with conservative speed.
    lane = {
        'name': f'HK {centre} traffic loop',
        'id': 1,
        'loop': True,
        'role': 3,
        'priorityOffset': 0,
        'points': points,
        'params': {
            'allowLaneChanges': False,
            'allowUTurns': True,
        },
    }
    data = {'lanes': [lane], 'intersections': [], 'areas': []}
    out = ROOT / 'content' / 'tracks' / track_id / 'data' / 'traffic.json'
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return out, len(points)


if __name__ == '__main__':
    targets = sys.argv[1:] or list(TRACKS)
    for track_id in targets:
        if track_id not in TRACKS:
            raise SystemExit(f'Unknown track: {track_id}')
        out, count = make_traffic(track_id, TRACKS[track_id])
        print(f'[OK] {track_id}: {count} points -> {out}')
