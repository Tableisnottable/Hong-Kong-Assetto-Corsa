"""Prepare a high-detail 1:1 road extract for the Tin Kwong Road exam corridor.

Reads the full-Hong-Kong OSM extract (build/HP1C/source/roads.osm.json) and
writes a compact corridor extract that the Blender HD generator consumes:

    build/HP1C/source/tin_kwong_hd_roads.json   (filtered ways + tags)
    build/HP1C/tin_kwong_road/roads_manifest.json (unique road names)

Usage:
    python tools/prepare_hd_map.py
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "build", "HP1C", "source", "roads.osm.json")
OUT = os.path.join(ROOT, "build", "HP1C", "source", "tin_kwong_hd_roads.json")
MANIFEST = os.path.join(ROOT, "build", "HP1C", "tin_kwong_road", "roads_manifest.json")

# Exam corridor around the Tin Kwong Road driving-test centre (~2.4 km x 2.4 km).
# Covers all three exam routes: Tin Kwong Road, Sheung Shing/Sheung Hong St,
# Ma Tau Wai Road, Farm Road, Argyle Street, Carlisle Road, Back Cheung Road...
BBOX = {"south": 22.312, "west": 114.170, "north": 22.334, "east": 114.198}

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


def inside_bbox(lat: float, lon: float) -> bool:
    return (
        BBOX["south"] <= lat <= BBOX["north"]
        and BBOX["west"] <= lon <= BBOX["east"]
    )


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


def main() -> None:
    if not os.path.exists(SRC):
        raise SystemExit(f"Source extract not found: {SRC}")

    print(f"[1/3] Loading {SRC} ...")
    with open(SRC, "r", encoding="utf-8") as f:
        data = json.load(f)

    kept = []
    road_names: dict[str, dict] = {}
    for element in data.get("elements", []):
        if element.get("type") != "way":
            continue
        tags = element.get("tags") or {}
        highway = tags.get("highway", "")
        if highway in EXCLUDED_HIGHWAYS:
            continue
        geometry = element.get("geometry") or []
        if not any(inside_bbox(p["lat"], p["lon"]) for p in geometry):
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
            key = name
            road_names.setdefault(key, {
                "name": name,
                "name:zh": tags.get("name:zh", ""),
                "name:en": tags.get("name:en", ""),
                "highway": highway,
                "maxspeed": tags.get("maxspeed", ""),
            })

    payload = {
        "boundary": BBOX,
        "reference": {"lat": 22.3219899, "lon": 114.1848273},
        "way_count": len(kept),
        "elements": kept,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(
            {"road_count": len(road_names),
             "roads": sorted(road_names.values(), key=lambda r: r["name"])},
            f, ensure_ascii=False, indent=2,
        )

    print(f"[2/3] Kept {len(kept)} drivable/buildable ways in the corridor.")
    print(f"[3/3] Wrote {OUT} and {MANIFEST} ({len(road_names)} named roads).")


if __name__ == "__main__":
    main()
