"""Download road source data for the Tin Kwong Road AC map.

The road geometry comes from OpenStreetMap's public Overpass API. Official
Hong Kong sources remain the survey/reference source and are recorded in the
manifest; Google Maps is deliberately not scraped or downloaded.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "HP1C" / "source"
OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"
MIN_REQUEST_INTERVAL_SECONDS = 15
MAX_RETRIES = 3
REQUEST_TIMEOUT_SECONDS = 90
QUERY = """
[out:json][timeout:60];
(
  way["highway"](22.314,114.178,22.324,114.191);
);
out geom tags;
"""


def fetch() -> dict:
    cached = OUT / "roads.osm.json"
    if cached.exists() and cached.stat().st_size > 0:
        print("Using cached road data:", cached)
        return json.loads(cached.read_text(encoding="utf-8"))

    OUT.mkdir(parents=True, exist_ok=True)
    print("Waiting before the single Overpass request...")
    time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
    request = Request(
        OVERPASS_URL,
        data=("data=" + QUERY).encode("utf-8"),
        headers={"User-Agent": "Hong-Kong-Assetto-Corsa-map-builder/0.1"},
        method="POST",
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            if attempt == MAX_RETRIES:
                raise
            delay = MIN_REQUEST_INTERVAL_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 3)
            print("Request failed; waiting %.1f seconds before retry %d/%d." %
                  (delay, attempt + 1, MAX_RETRIES))
            time.sleep(delay)


def to_geojson(payload: dict) -> dict:
    features = []
    for element in payload.get("elements", []):
        geometry = element.get("geometry", [])
        if len(geometry) < 2:
            continue
        features.append({
            "type": "Feature",
            "properties": element.get("tags", {}),
            "geometry": {
                "type": "LineString",
                "coordinates": [[point["lon"], point["lat"]] for point in geometry],
            },
        })
    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = fetch()
    (OUT / "roads.osm.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "roads.geojson").write_text(
        json.dumps(to_geojson(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest = {
        "map": "tin_kwong_road",
        "survey_group": "HP1C",
        "sheet": "11-SW-9D",
        "sources": [
            {
                "name": "OpenStreetMap Overpass",
                "url": OVERPASS_URL,
                "purpose": "road centerline and road names",
                "license": "ODbL 1.0",
            },
            {
                "name": "Hong Kong GeoInfo Map",
                "url": "https://www.map.gov.hk/gm/",
                "purpose": "official visual and coordinate reference",
            },
            {
                "name": "Lands Department eHongKongStreet",
                "url": "https://www.landsd.gov.hk/tc/resources/mapping-information/ehkg.html",
                "purpose": "official GeoPDF map reference",
            },
        ],
        "google_maps": "manual_reference_only_no_download",
        "request_policy": {
            "concurrent_requests": 1,
            "minimum_interval_seconds": MIN_REQUEST_INTERVAL_SECONDS,
            "retries": MAX_RETRIES,
            "cache_enabled": True,
        },
        "downloaded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (OUT / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Downloaded", len(to_geojson(payload)["features"]), "road features to", OUT)


if __name__ == "__main__":
    main()
