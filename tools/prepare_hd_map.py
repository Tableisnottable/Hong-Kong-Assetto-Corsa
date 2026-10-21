"""Prepare high-detail 1:1 road extracts for all HK driving-test centres.

Reads the full-Hong-Kong OSM extract (build/HP1C/source/roads.osm.json) and
writes compact corridor extracts that the Blender HD generator consumes:

    build/HP1C/source/<centre>_hd_roads.json        (filtered ways + tags)
    build/HP1C/<centre>/roads_manifest.json         (unique road names)

Usage:
    python tools/prepare_hd_map.py                    # all centres
    python tools/prepare_hd_map.py tin_kwong_road     # one centre
    python tools/prepare_hd_map.py --list             # list centres
"""

from __future__ import annotations

import argparse
import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build", "HP1C", "source", "roads.osm.json")
OUT_DIR = os.path.join(ROOT, "build", "HP1C", "source")
MANIFEST_DIR = os.path.join(ROOT, "build", "HP1C")

# Test centres with approximate centre coordinates and corridor size.
# (lat, lon) are WGS84; size_km is the corridor half-extent in km.
CENTRES = {
    "tin_kwong_road": {
        "name": "天光道", "lat": 22.322, "lon": 114.185, "size_km": 2.4,
        "note": "九龍土瓜灣 - 私家車/輕型貨車考場",
        # Exact original corridor bbox (preserves the 5,578-way extract)
        "bbox": {"south": 22.312, "west": 114.170, "north": 22.334, "east": 114.198},
    },
    "sheung_on_street": {
        "name": "柴灣常安街", "lat": 22.264, "lon": 114.243, "size_km": 2.4,
        "note": "港島柴灣 - 巴士/小巴考場",
    },
    "texaco_road": {
        "name": "荃灣德士古道", "lat": 22.365, "lon": 114.115, "size_km": 3.0,
        "note": "新界荃灣 - 中型/重型貨車/巴士考場",
    },
    "happy_valley": {
        "name": "跑馬地", "lat": 22.269, "lon": 114.186, "size_km": 2.0,
        "note": "港島 - 私家車考場",
    },
    "so_kun_po": {
        "name": "掃桿埔", "lat": 22.273, "lon": 114.192, "size_km": 2.0,
        "note": "港島 - 輕型貨車考場",
    },
    "shek_am": {
        "name": "石蔭", "lat": 22.369, "lon": 114.138, "size_km": 2.0,
        "note": "新界葵涌 - 私家車/輕型貨車考場",
    },
    "yau_tong": {
        "name": "油塘", "lat": 22.296, "lon": 114.235, "size_km": 2.0,
        "note": "九龍油塘 - 輕型貨車考場",
    },
    "chung_ngai_street": {
        "name": "忠義街", "lat": 22.3175, "lon": 114.1745, "size_km": 2.0,
        "note": "九龍何文田 - 私家車/輕型貨車考場",
    },
    "pui_ching_road": {
        "name": "培正道", "lat": 22.3179742, "lon": 114.1773149, "size_km": 2.0,
        "note": "九龍何文田 - 私家車/輕型貨車考場",
    },
    "wing_hau_street": {
        "name": "永孝街", "lat": 22.3155, "lon": 114.1885, "size_km": 2.0,
        "note": "九龍土瓜灣 - 私家車/輕型貨車考場",
    },
    "ap_lei_chau": {
        "name": "鴨脷洲", "lat": 22.2399354, "lon": 114.1545244, "size_km": 2.0,
        "note": "港島南區 - 安全駕駛中心",
    },
    "yuen_long": {
        "name": "元朗南生圍", "lat": 22.4623971, "lon": 114.0379722, "size_km": 2.5,
        "note": "新界元朗 - 安全駕駛中心",
    },
    "sha_tin": {
        "name": "沙田小瀝源", "lat": 22.3887506, "lon": 114.2033455, "size_km": 2.0,
        "note": "新界沙田 - 安全駕駛中心",
    },
}

# Non-drivable / non-buildable highway types to drop.
EXCLUDED_HIGHWAYS = {
    "path", "steps", "bridleway", "track", "corridor", "elevator", "platform",
    "construction", "proposed", "raceway", "trailhead", "emergency_bay",
    "rest_area", "bus_stop", "road", "escape", "ladder", "junction",
    "traffic_island", "disused",
}

KEEP_TAGS = [
    "highway", "lanes", "oneway", "surface", "layer", "name", "name:zh",
    "name:en", "maxspeed", "crossing", "bridge", "junction",
]


def simplify(pts: list[dict], min_distance: float = 0.8) -> list[dict]:
    """Drop consecutive points closer than min_distance (metres, approx)."""
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for p in pts[1:]:
        dx = (p["lon"] - out[-1]["lon"]) * 102_900.0
        dy = (p["lat"] - out[-1]["lat"]) * 111_000.0
        if dx * dx + dy * dy >= min_distance * min_distance:
            out.append(p)
    if out[-1] is not pts[-1]:
        out.append(pts[-1])
    return out


def prepare_centre(centre_id: str, centre: dict, elements: list) -> dict:
    """Extract ways within the centre's corridor. Returns stats."""
    if "bbox" in centre:
        lat0 = centre["bbox"]["south"]
        lat1 = centre["bbox"]["north"]
        lon0 = centre["bbox"]["west"]
        lon1 = centre["bbox"]["east"]
    else:
        half = centre["size_km"] / 2 / 111.0  # degrees lat
        lat0, lat1 = centre["lat"] - half, centre["lat"] + half
        lon_half = half / max(0.7, math.cos(math.radians(centre["lat"])))
        lon0, lon1 = centre["lon"] - lon_half, centre["lon"] + lon_half

    kept = []
    road_names: dict[str, dict] = {}
    for element in elements:
        if element.get("type") != "way":
            continue
        tags = element.get("tags") or {}
        highway = tags.get("highway", "")
        if highway in EXCLUDED_HIGHWAYS:
            continue
        geometry = element.get("geometry") or []
        if not any(lat0 <= p["lat"] <= lat1 and lon0 <= p["lon"] <= lon1
                   for p in geometry):
            continue

        clean = simplify(geometry)
        if len(clean) < 2:
            continue

        kept.append({
            "id": element["id"],
            "tags": {k: tags[k] for k in KEEP_TAGS if k in tags},
            "geometry": clean,
        })

        name = tags.get("name") or tags.get("name:zh") or tags.get("name:en")
        if name:
            road_names.setdefault(name, {
                "name": name,
                "name:zh": tags.get("name:zh", ""),
                "name:en": tags.get("name:en", ""),
                "highway": highway,
                "maxspeed": tags.get("maxspeed", ""),
            })

    payload = {
        "centre": centre_id,
        "centre_name": centre["name"],
        "note": centre.get("note", ""),
        "boundary": {"south": lat0, "west": lon0, "north": lat1, "east": lon1},
        "reference": {"lat": centre["lat"], "lon": centre["lon"]},
        "way_count": len(kept),
        "elements": kept,
    }

    out = os.path.join(OUT_DIR, f"{centre_id}_hd_roads.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    manifest_path = os.path.join(MANIFEST_DIR, centre_id, "roads_manifest.json")
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {"centre": centre_id, "road_count": len(road_names),
             "roads": sorted(road_names.values(), key=lambda r: r["name"])},
            f, ensure_ascii=False, indent=2,
        )

    return {"centre": centre_id, "name": centre["name"],
            "ways": len(kept), "roads": len(road_names), "file": out}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare HD road extracts")
    parser.add_argument("centres", nargs="*", help="centre ids (default: all)")
    parser.add_argument("--list", action="store_true", help="list centres")
    args = parser.parse_args()

    if args.list:
        for cid, c in CENTRES.items():
            print(f"  {cid}: {c['name']} ({c['note']})")
        return

    if not os.path.exists(SRC):
        raise SystemExit(f"Source extract not found: {SRC}")

    targets = args.centres or list(CENTRES.keys())
    print(f"[1/2] Loading {SRC} ...")
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)
    elements = data.get("elements", [])
    print(f"      {len(elements)} ways loaded")

    print(f"[2/2] Preparing {len(targets)} centres ...")
    results = []
    for cid in targets:
        if cid not in CENTRES:
            print(f"  [!] Unknown centre: {cid} (use --list)")
            continue
        r = prepare_centre(cid, CENTRES[cid], elements)
        results.append(r)
        print(f"  [OK] {r['centre']} ({r['name']}): "
              f"{r['ways']} ways, {r['roads']} named roads -> {r['file']}")

    print(f"[DONE] Prepared {len(results)} centre extracts.")


if __name__ == "__main__":
    main()
