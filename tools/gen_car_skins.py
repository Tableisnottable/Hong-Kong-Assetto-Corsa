# -*- coding: utf-8 -*-
"""Complete the car UI metadata and give every car usable skins.

Two gaps found when comparing against a working AC car
(hk51_traffic_toyota_camry):

1. ui_car.json was missing the fields AC reads for the showroom and car
   list: author, version, year, country, url, torqueCurve/powerCurve and
   a couple of specs keys. Without `year` AC also leaves the car out of
   some filters.

2. skins/ contained only a README — no skin.ini and no livery, so the car
   had no paintable skin and AC showed a single unusable entry.

This script rewrites ui_car.json with the full field set and generates
several HK-appropriate skins per car, each with a proper skin.ini and a
solid-colour livery PNG.

Usage:
    python tools/gen_car_skins.py
"""

import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / "content" / "cars"

# Skin sets per vehicle class, in the colours that actually appear in HK.
SKINS = {
    "default": {
        "sedan": [
            ("Pearl White", (238, 238, 236)),
            ("Silver", (176, 180, 184)),
            ("Graphite", (58, 60, 63)),
            ("Deep Blue", (26, 48, 92)),
        ],
        "van": [
            ("White", (240, 240, 238)),
            ("Silver", (172, 176, 180)),
            ("Fleet Blue", (36, 62, 118)),
        ],
        "bus": [
            ("ADL White", (242, 242, 240)),
            ("KMB Red", (168, 32, 38)),
            ("Citybus Yellow", (232, 176, 28)),
        ],
        "taxi": [
            ("Urban Red", (176, 28, 34)),
            ("NT Green", (28, 116, 68)),
        ],
    }
}


def solid_png(path: Path, rgb, size: int = 64) -> None:
    """Write a solid-colour PNG (used as the skin livery)."""
    r, g, b = rgb
    row = bytes((0,)) + bytes((r, g, b, 255)) * size
    raw = row * size

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9))
    data += chunk(b"IEND", b"")
    path.write_bytes(data)


def car_kind(car_id: str, ui: dict) -> str:
    tags = " ".join(ui.get("tags", [])).lower()
    cls = str(ui.get("class", "")).lower()
    if "cat17" in car_id or "bus" in tags:
        return "bus"
    if "taxi" in tags:
        return "taxi"
    if "hiace" in car_id or "van" in tags:
        return "van"
    return "sedan"


def ensure_ui(car_dir: Path) -> dict:
    ui_path = car_dir / "ui" / "ui_car.json"
    ui = json.loads(ui_path.read_text(encoding="utf-8")) if ui_path.exists() else {}
    ui.setdefault("name", car_dir.name)
    ui.setdefault("brand", "Hong Kong")
    ui.setdefault("class", "street")
    ui.setdefault("tags", ["hongkong"])
    ui.setdefault("specs", {})

    # Fields AC uses but we never set.
    ui.setdefault("author", "Hong Kong AC Project")
    ui.setdefault("version", "1.0")
    ui.setdefault("url", "https://github.com/Tableisnottable/Hong-Kong-Assetto-Corsa")
    ui.setdefault("country", "Hong Kong")
    ui.setdefault("year", 2022)
    ui.setdefault("torqueCurve", "power.lut")
    ui.setdefault("powerCurve", "power.lut")

    specs = ui["specs"]
    if "bhp" not in specs and "power" in specs:
        # Derive a numeric bhp so AC can sort by power.
        digits = "".join(ch for ch in str(specs["power"]).split("@")[0] if ch.isdigit())
        if digits:
            specs["bhp"] = int(digits)
    specs.setdefault("weight", specs.get("kerb_weight", "n/a"))
    specs.setdefault("torque", "n/a")
    specs.setdefault("topspeed", "n/a")
    specs.setdefault("acceleration", "n/a")

    ui_path.parent.mkdir(parents=True, exist_ok=True)
    ui_path.write_text(json.dumps(ui, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ui


def ensure_skins(car_dir: Path, ui: dict) -> int:
    kind = car_kind(car_dir.name, ui)
    palette = SKINS["default"][kind]
    skins_root = car_dir / "skins"
    skins_root.mkdir(parents=True, exist_ok=True)

    # Remove the placeholder README-only skin.
    placeholder = skins_root / "default"
    if placeholder.is_dir() and not (placeholder / "skin.ini").exists():
        for item in placeholder.iterdir():
            item.unlink()
        placeholder.rmdir()

    count = 0
    for index, (name, rgb) in enumerate(palette):
        folder = skins_root / ("00-default" if index == 0 else f"{index:02d}-{name.lower().replace(' ', '-')}")
        folder.mkdir(parents=True, exist_ok=True)
        solid_png(folder / "livery.png", rgb)
        (folder / "skin.ini").write_text(
            "[SKIN]\n"
            f"NAME={name}\n"
            f"SKINNAME={name}\n"
            "AUTHOR=Hong Kong AC Project\n"
            "DESCRIPTION=Hong Kong exam vehicle livery\n"
            "SKINNED_TEXTURE_0=livery.png\n",
            encoding="utf-8",
        )
        count += 1
    return count


def main() -> None:
    total_cars = 0
    total_skins = 0
    for car_dir in sorted(CARS.iterdir()):
        if not car_dir.is_dir() or not car_dir.name.startswith("hk_cat"):
            continue
        ui = ensure_ui(car_dir)
        n = ensure_skins(car_dir, ui)
        total_cars += 1
        total_skins += n
        print(f"[OK] {car_dir.name}: ui_car completed, {n} skins")
    print(f"\n{total_cars} cars, {total_skins} skins total")


if __name__ == "__main__":
    main()
