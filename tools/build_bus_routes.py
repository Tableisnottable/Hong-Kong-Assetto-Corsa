# -*- coding: utf-8 -*-
"""Build a Hong Kong bus route catalogue for the 13 driving-test centres.

Sources (HK Open Data):
    KMB  https://data.etabus.gov.hk/v1/transport/kmb/route/
    CTB  https://rt.data.gov.hk/v2/transport/citybus/route/CTB

The catalogue records, per operator, the routes whose origin/destination or
stop names mention a centre's district. It is used to pick realistic bus
vehicle types when generating CSP traffic and to show route context in the
exam app.

Output: config/bus_routes_hk.json
Usage:  python tools/build_bus_routes.py [--districts]
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "bus_routes_hk.json"

KMB_ROUTES = "https://data.etabus.gov.hk/v1/transport/kmb/route/"
CTB_ROUTES = "https://rt.data.gov.hk/v2/transport/citybus/route/CTB"

# District keywords used to associate a route with a test-centre corridor.
CENTRE_KEYWORDS = {
    "tin_kwong_road": ["土瓜灣", "To Kwa Wan", "馬頭圍", "Ma Tau Wai", "何文田", "Ho Man Tin", "紅磡", "Hung Hom"],
    "sheung_on_street": ["柴灣", "Chai Wan", "筲箕灣", "Shau Kei Wan"],
    "texaco_road": ["荃灣", "Tsuen Wan", "葵涌", "Kwai Chung"],
    "happy_valley": ["跑馬地", "Happy Valley", "灣仔", "Wan Chai", "銅鑼灣", "Causeway Bay"],
    "so_kun_po": ["掃桿埔", "So Kon Po", "銅鑼灣", "Causeway Bay", "大坑", "Tai Hang"],
    "shek_am": ["石蔭", "Shek Yam", "葵涌", "Kwai Chung", "梨木樹", "Lei Muk Shue"],
    "yau_tong": ["油塘", "Yau Tong", "藍田", "Lam Tin", "觀塘", "Kwun Tong"],
    "chung_ngai_street": ["何文田", "Ho Man Tin", "紅磡", "Hung Hom", "愛民", "Oi Man"],
    "pui_ching_road": ["何文田", "Ho Man Tin", "培正", "Pui Ching", "九龍城", "Kowloon City"],
    "wing_hau_street": ["土瓜灣", "To Kwa Wan", "九龍城", "Kowloon City", "馬頭角", "Ma Tau Kok"],
    "ap_lei_chau": ["鴨脷洲", "Ap Lei Chau", "香港仔", "Aberdeen", "利東", "Lei Tung"],
    "yuen_long": ["元朗", "Yuen Long", "南生圍", "Nam Sang Wai", "天水圍", "Tin Shui Wai"],
    "sha_tin": ["沙田", "Sha Tin", "小瀝源", "Siu Lek Yuen", "石門", "Shek Mun", "馬鞍山", "Ma On Shan"],
}


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "HK-AC-Project/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fetch_kmb() -> list[dict]:
    payload = get_json(KMB_ROUTES)
    routes = []
    for r in payload.get("data", []):
        routes.append({
            "operator": "KMB",
            "route": r.get("route", ""),
            "bound": r.get("bound", ""),
            "orig_tc": r.get("orig_tc", ""),
            "dest_tc": r.get("dest_tc", ""),
            "orig_en": r.get("orig_en", ""),
            "dest_en": r.get("dest_en", ""),
        })
    return routes


def fetch_ctb() -> list[dict]:
    payload = get_json(CTB_ROUTES)
    routes = []
    for r in payload.get("data", []):
        routes.append({
            "operator": "CTB",
            "route": r.get("route", ""),
            "bound": "O",
            "orig_tc": r.get("orig_tc", ""),
            "dest_tc": r.get("dest_tc", ""),
            "orig_en": r.get("orig_en", ""),
            "dest_en": r.get("dest_en", ""),
        })
    return routes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--districts", action="store_true", help="only print centre matches")
    args = ap.parse_args()

    print("Fetching KMB routes...")
    kmb = fetch_kmb()
    print(f"  {len(kmb)} KMB entries")
    print("Fetching CTB routes...")
    ctb = fetch_ctb()
    print(f"  {len(ctb)} CTB entries")

    all_routes = kmb + ctb

    # Deduplicate by operator+route+bound.
    seen = set()
    unique = []
    for r in all_routes:
        key = (r["operator"], r["route"], r["bound"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    per_centre = {}
    for centre, keywords in CENTRE_KEYWORDS.items():
        matches = []
        for r in unique:
            haystack = " ".join((r["orig_tc"], r["dest_tc"], r["orig_en"], r["dest_en"]))
            if any(k in haystack for k in keywords):
                matches.append(f'{r["operator"]} {r["route"]}')
        per_centre[centre] = sorted(set(matches))

    payload = {
        "source": {"kmb": KMB_ROUTES, "ctb": CTB_ROUTES},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_routes": len(unique),
        "by_operator": {
            "KMB": sum(1 for r in unique if r["operator"] == "KMB"),
            "CTB": sum(1 for r in unique if r["operator"] == "CTB"),
        },
        "centre_keywords": CENTRE_KEYWORDS,
        "routes_by_centre": per_centre,
        "routes": unique,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {len(unique)} unique routes -> {OUT.name}")

    if args.districts:
        for centre, routes in per_centre.items():
            print(f"  {centre}: {len(routes)} routes")


if __name__ == "__main__":
    main()
