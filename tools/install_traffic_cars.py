# -*- coding: utf-8 -*-
"""Install HK traffic cars into the CSP Traffic Tool data folder.

Copies each car's LOD C (low-poly) model into
extension/lua/tools/csp-traffic-tool/data/ and writes a CarDefinition
JSON so CSP Traffic mode can spawn real Hong Kong vehicles.

Source of truth: config/traffic_cars.json (AC folders + specs).

Usage:
    python tools/install_traffic_cars.py            # all cars
    python tools/install_traffic_cars.py camry      # one car (id suffix)
"""

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AC_CARS = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
CSP_TOOL = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa\extension\lua\tools\csp-traffic-tool")
DATA_DIR = CSP_TOOL / "data"


def guess_chance(category: str) -> float:
    """Traffic mix weighting: private cars most common, trucks/buses rare."""
    return {
        "private": 1.0,
        "commercial": 0.3,
        "public_special": 0.2,
    }.get(category, 0.5)


def guess_dimensions(category: str) -> dict:
    """Approximate physical dimensions per vehicle class."""
    if category == "public_special":
        return {"width": 2.4, "fakeShadowZ": 3.6, "turningOffset": 3.4, "wheelRadius": 0.42, "front": 1.2, "rear": 6.0, "fakeShadowX": 1.6}
    if category == "commercial":
        return {"width": 2.2, "fakeShadowZ": 3.4, "turningOffset": 3.2, "wheelRadius": 0.40, "front": 1.2, "rear": 5.5, "fakeShadowX": 1.5}
    return {"width": 1.7, "fakeShadowZ": 2.6, "turningOffset": 2.3, "wheelRadius": 0.33, "front": 0.5, "rear": 4.0, "fakeShadowX": 1.15}


def guess_mass(category: str) -> int:
    return {"private": 1400, "commercial": 3500, "public_special": 9000}.get(category, 1800)


def main() -> None:
    with open(ROOT / "config" / "traffic_cars.json", encoding="utf-8") as f:
        registry = json.load(f)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filters = sys.argv[1:]
    installed = 0
    for car in registry["cars"]:
        cid = car["id"]
        if filters and not any(f in cid for f in filters):
            continue
        folder = car["ac_folder"]
        src_dir = AC_CARS / folder
        if not src_dir.is_dir():
            print(f"[SKIP] {cid}: {src_dir} missing")
            continue

        # Prefer a _lod_c model; fall back to any _lod, then main body.
        lods = sorted(car.get("lods", []))
        lod_c = next((f for f in lods if "_lod_c" in f.lower()), None)
        lod = lod_c or (lods[0] if lods else None)
        main_candidates = [car.get("kn5")] if car.get("kn5") else []
        main_file = next((f for f in main_candidates if f and (src_dir / f).exists()), None)
        if not main_file:
            # discover <folder>.kn5
            for f in os.listdir(src_dir):
                if f.endswith(".kn5") and not f.startswith("collider") and "_lod" not in f.lower():
                    main_file = f
                    break
        collider = "collider.kn5" if (src_dir / "collider.kn5").exists() else None
        if not main_file or not lod or not collider:
            print(f"[SKIP] {cid}: missing main/lod/collider")
            continue

        prefix = "hk_" + cid
        # Copy files with a stable prefix.
        dest_main = DATA_DIR / f"{prefix}.kn5"
        dest_lod = DATA_DIR / f"{prefix}_lod.kn5"
        dest_collider = DATA_DIR / f"{prefix}_collider.kn5"
        shutil.copy2(src_dir / main_file, dest_main)
        shutil.copy2(src_dir / lod, dest_lod)
        shutil.copy2(src_dir / collider, dest_collider)

        # CarDefinition JSON
        definition = {
            "main": f"{prefix}.kn5",
            "lod": f"{prefix}_lod.kn5",
            "collider": f"{prefix}_collider.kn5",
            "color": "vintage" if car.get("year", 2015) < 2015 else "modern",
            "maxSpeed": max(60, int(car.get("power_hp", 120) * 0.55)),
            "dynamic": 0.8 if car.get("category") == "private" else 0.5,
            "chance": guess_chance(car.get("category")),
            "dimensions": guess_dimensions(car.get("category")),
            "physics": {
                "width": guess_dimensions(car.get("category"))["width"] * 0.92,
                "suspensionForce": 30,
                "mass": guess_mass(car.get("category")),
                "suspensionTravel": 0.08,
                "wheelsGripForce": 8,
                "suspensionDamping": 14,
                "length": guess_dimensions(car.get("category"))["fakeShadowZ"],
            },
        }
        dest_json = DATA_DIR / f"{prefix}.json"
        dest_json.write_text(json.dumps(definition, ensure_ascii=False, indent=2), encoding="utf-8")
        installed += 1
        print(f"[OK] {cid}: {main_file} + {lod} + collider -> {prefix}")

    print(f"\nInstalled {installed}/{len(registry['cars'])} cars into {DATA_DIR}")


if __name__ == "__main__":
    main()
