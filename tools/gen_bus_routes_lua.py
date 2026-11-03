# -*- coding: utf-8 -*-
"""Generate apps/lua/hk_exam/bus_routes.lua from config/bus_routes_hk.json.

Keeps the in-game app lightweight: only route codes per test centre.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "config" / "bus_routes_hk.json"
OUT = ROOT / "apps" / "lua" / "hk_exam" / "bus_routes.lua"

CENTRE_TO_TRACK = {
    "tin_kwong_road": "hong_kong_1to1",
    "sheung_on_street": "hong_kong_1to1_sheung_on",
    "texaco_road": "hong_kong_1to1_texaco",
    "happy_valley": "hong_kong_1to1_happy_valley",
    "so_kun_po": "hong_kong_1to1_so_kun_po",
    "shek_am": "hong_kong_1to1_shek_am",
    "yau_tong": "hong_kong_1to1_yau_tong",
    "chung_ngai_street": "hong_kong_1to1_chung_ngai",
    "pui_ching_road": "hong_kong_1to1_pui_ching",
    "wing_hau_street": "hong_kong_1to1_wing_hau",
    "ap_lei_chau": "hong_kong_1to1_ap_lei_chau",
    "yuen_long": "hong_kong_1to1_yuen_long",
    "sha_tin": "hong_kong_1to1_sha_tin",
}


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    by_centre = data.get("routes_by_centre", {})

    lines = [
        "-- HK bus routes serving each test-centre district (auto-generated)",
        "-- Source: data.etabus.gov.hk (KMB) + rt.data.gov.hk (CTB)",
        f"-- Generated: {data.get('fetched_at', '')}",
        "",
        "return {",
    ]
    count = 0
    for centre, routes in sorted(by_centre.items()):
        track = CENTRE_TO_TRACK.get(centre, centre)
        codes = []
        seen = set()
        for r in routes:
            code = r.split(" ", 1)[-1]
            if code in seen:
                continue
            seen.add(code)
            codes.append(code)
        count += len(codes)
        lines.append(f'  ["{track}"] = {{')
        # Wrap 10 per line for readability.
        for i in range(0, len(codes), 10):
            chunk = ", ".join(f'"{c}"' for c in codes[i:i + 10])
            lines.append(f"    {chunk},")
        lines.append("  },")
    lines.append("}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] {count} route codes across {len(by_centre)} centres -> {OUT.name}")


if __name__ == "__main__":
    main()
