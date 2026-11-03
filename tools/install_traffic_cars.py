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


# Real-world dimensions per vehicle id (length, width, height, wheelbase, mass kg)
SPECS = {
    "traffic_toyota_camry": (4.88, 1.84, 1.44, 2.83, 1560),
    "traffic_toyota_alphard": (4.95, 1.85, 1.95, 3.00, 2100),
    "traffic_toyota_crown_comfort": (4.69, 1.70, 1.51, 2.79, 1420),
    "traffic_toyota_prius_taxi": (4.58, 1.76, 1.49, 2.70, 1420),
    "traffic_toyota_hiace": (4.84, 1.88, 1.98, 3.11, 1900),
    "traffic_toyota_coaster": (6.99, 2.08, 2.75, 3.94, 4500),
    "traffic_honda_jazz": (4.04, 1.70, 1.53, 2.53, 1120),
    "traffic_bus_volvo_olympian": (11.90, 2.50, 4.40, 5.60, 16000),
    "traffic_isuzu_giga": (11.20, 2.49, 3.30, 6.20, 12000),
    "traffic_isuzu_npr_flatbed": (6.60, 2.06, 2.30, 3.36, 4200),
    "traffic_mercedes_a45": (4.36, 1.78, 1.42, 2.70, 1480),
    "traffic_nissan_gtr": (4.71, 1.89, 1.37, 2.78, 1750),
    "traffic_porsche_macan": (4.70, 1.92, 1.62, 2.81, 1880),
    "traffic_tesla_model3": (4.69, 1.85, 1.44, 2.88, 1700),
    "traffic_vw_golf_r": (4.26, 1.79, 1.46, 2.63, 1470),
    "traffic_mitsubishi_colt": (3.99, 1.63, 1.37, 2.46, 950),
    "traffic_mule_truck": (4.80, 1.85, 2.20, 2.80, 2600),
    "traffic_ff_truck": (7.20, 2.30, 3.10, 4.00, 6500),
    "traffic_suzuki_gsxr": (2.05, 0.72, 1.13, 1.41, 200),
    "traffic_celica": (4.35, 1.74, 1.31, 2.54, 1260),
    "traffic_hiace_popo": (4.84, 1.88, 1.98, 3.11, 2000),
    "traffic_airport_bus": (12.00, 2.55, 4.30, 5.80, 17000),
}


def guess_dimensions(category: str) -> dict:
    """Fallback dimensions per class when no real spec is registered."""
    if category == "public_special":
        return {"width": 2.4, "fakeShadowZ": 3.6, "turningOffset": 3.4, "wheelRadius": 0.42, "front": 1.2, "rear": 6.0, "fakeShadowX": 1.6}
    if category == "commercial":
        return {"width": 2.2, "fakeShadowZ": 3.4, "turningOffset": 3.2, "wheelRadius": 0.40, "front": 1.2, "rear": 5.5, "fakeShadowX": 1.5}
    return {"width": 1.7, "fakeShadowZ": 2.6, "turningOffset": 2.3, "wheelRadius": 0.33, "front": 0.5, "rear": 4.0, "fakeShadowX": 1.15}


def dimensions_for(cid: str, category: str) -> dict:
    """Build a CarDefinition dimensions block from real specs when known."""
    spec = SPECS.get(cid)
    if not spec:
        return guess_dimensions(category)
    length, width, height, wheelbase, _mass = spec
    # CSP expects front/rear as distances from the axle midpoint to the bumpers.
    overhang = max(0.4, (length - wheelbase) / 2)
    return {
        "width": round(width, 2),
        "fakeShadowZ": round(length / 2 + 0.15, 2),
        "turningOffset": round(wheelbase / 2, 2),
        "wheelRadius": 0.42 if height > 2.0 else 0.33,
        "front": round(overhang, 2),
        "rear": round(length - overhang, 2),
        "fakeShadowX": round(width / 2 + 0.3, 2),
    }


def mass_for(cid: str, category: str) -> int:
    spec = SPECS.get(cid)
    if spec:
        return spec[4]
    return {"private": 1400, "commercial": 3500, "public_special": 9000}.get(category, 1800)


def max_speed_for(cid: str, category: str) -> int:
    """Realistic top speed in km/h for traffic behaviour."""
    return {
        "private": 140,
        "commercial": 90,
        "public_special": 85,
    }.get(category, 110)


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

        # CarDefinition JSON built from real specs where available.
        dims = dimensions_for(cid, car.get("category"))
        definition = {
            "main": f"{prefix}.kn5",
            "lod": f"{prefix}_lod.kn5",
            "collider": f"{prefix}_collider.kn5",
            "color": "vintage" if car.get("year", 2015) < 2015 else "modern",
            "maxSpeed": max_speed_for(cid, car.get("category")),
            "dynamic": 0.8 if car.get("category") == "private" else 0.5,
            "chance": guess_chance(car.get("category")),
            "dimensions": dims,
            "physics": {
                "width": round(dims["width"] * 0.9, 2),
                "suspensionForce": 30 if car.get("category") == "private" else 48,
                "mass": mass_for(cid, car.get("category")),
                "suspensionTravel": 0.08 if car.get("category") == "private" else 0.12,
                "wheelsGripForce": 8 if car.get("category") == "private" else 12,
                "suspensionDamping": 14 if car.get("category") == "private" else 20,
                "length": round(dims["fakeShadowZ"] * 2 - 0.3, 2),
            },
        }
        dest_json = DATA_DIR / f"{prefix}.json"
        dest_json.write_text(json.dumps(definition, ensure_ascii=False, indent=2), encoding="utf-8")
        installed += 1
        print(f"[OK] {cid}: {main_file} + {lod} + collider -> {prefix}")

    print(f"\nInstalled {installed}/{len(registry['cars'])} cars into {DATA_DIR}")


if __name__ == "__main__":
    main()
