# -*- coding: utf-8 -*-
"""Download OSM building footprints for all test centre corridors.

Queries Overpass API for way["building"] / way["building:part"] within
each centre's corridor bbox and saves the result to
build/HP1C/source/<centre>_buildings.json

Usage:
    python tools/fetch_buildings.py              # all centres
    python tools/fetch_buildings.py tin_kwong_road  # one centre
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "build" / "HP1C" / "source"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Centre corridors (match tools/prepare_hd_map.py)
CENTRES = {
    "tin_kwong_road": {"south": 22.312, "west": 114.170, "north": 22.334, "east": 114.198},
    "sheung_on_street": {"south": 22.254, "west": 114.233, "north": 22.274, "east": 114.253},
    "texaco_road": {"south": 22.350, "west": 114.100, "north": 22.380, "east": 114.130},
    "happy_valley": {"south": 22.259, "west": 114.176, "north": 22.279, "east": 114.196},
    "so_kun_po": {"south": 22.263, "west": 114.182, "north": 22.283, "east": 114.202},
    "shek_am": {"south": 22.359, "west": 114.128, "north": 22.379, "east": 114.148},
    "yau_tong": {"south": 22.286, "west": 114.225, "north": 22.306, "east": 114.245},
    "chung_ngai_street": {"south": 22.3075, "west": 114.1645, "north": 22.3275, "east": 114.1845},
    "pui_ching_road": {"south": 22.3080, "west": 114.1673, "north": 22.3280, "east": 114.1873},
    "wing_hau_street": {"south": 22.3055, "west": 114.1785, "north": 22.3255, "east": 114.1985},
    "ap_lei_chau": {"south": 22.2299, "west": 114.1445, "north": 22.2499, "east": 114.1645},
    "yuen_long": {"south": 22.4524, "west": 114.0280, "north": 22.4724, "east": 114.0480},
    "sha_tin": {"south": 22.3788, "west": 114.1933, "north": 22.3988, "east": 114.2133},
}


MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def _query(query_text: str) -> dict:
    """POST a query, rotating mirrors and retrying on transient failures."""
    last_err = None
    for attempt in range(6):
        mirror = MIRRORS[attempt % len(MIRRORS)]
        try:
            req = urllib.request.Request(
                mirror,
                data=query_text.encode("utf-8"),
                headers={"User-Agent": "HK-AC-Project/1.0"},
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:  # rate limits, 502/504, partial reads
            last_err = e
            wait = min(60, 8 * (attempt + 1))
            print(f"    retry {attempt + 1}/6 in {wait}s ({type(e).__name__})")
            time.sleep(wait)
    raise RuntimeError(f"all mirrors failed: {last_err}")


def fetch(centre: str) -> int:
    bbox = CENTRES[centre]
    bb = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
    query = f"""
[out:json][timeout:90];
(
  way["building"]({bb});
  way["building:part"]({bb});
  node["natural"="tree"]({bb});
  way["landuse"~"^(grass|forest|park|recreation_ground|village_green|meadow)$"]({bb});
  way["leisure"~"^(park|garden|pitch|playground|golf_course)$"]({bb});
);
out body geom;
"""
    resp = _query(query)
    elements = resp.get("elements", [])
    out = OUT_DIR / f"{centre}_buildings.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"centre": centre, "count": len(elements), "elements": elements},
                  f, ensure_ascii=False)
    return len(elements)


def main() -> None:
    targets = sys.argv[1:] or list(CENTRES)
    for centre in targets:
        if centre not in CENTRES:
            print(f"[!] Unknown centre: {centre}")
            continue
        try:
            n = fetch(centre)
            print(f"[OK] {centre}: {n} buildings -> build/HP1C/source/{centre}_buildings.json")
        except Exception as e:
            print(f"[ERR] {centre}: {type(e).__name__}: {e}")
        time.sleep(8)  # respect Overpass rate limits


if __name__ == "__main__":
    main()
