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


def _curve_pairs(car_dir: Path, target_points: int = 96) -> tuple[list, list]:
    """Convert data/power.lut into AC's ui_car powerCurve/torqueCurve arrays.

    AC expects a list of [rpm, value] pairs and draws a smooth line from them.
    power.lut holds torque in Nm but only ~13 rows, so the points are
    interpolated up to `target_points` for a smooth showroom graph.
    powerCurve is derived as kW = Nm * rpm / 9549.
    """
    lut = car_dir / "data" / "power.lut"
    if not lut.exists():
        return [], []

    samples: list[tuple[float, float]] = []
    for line in lut.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(";") or "|" not in line:
            continue
        rpm_s, nm_s = line.split("|", 1)
        try:
            samples.append((float(rpm_s), float(nm_s)))
        except ValueError:
            continue
    if len(samples) < 2:
        return [], []

    def torque_at(rpm: float) -> float:
        if rpm <= samples[0][0]:
            return samples[0][1]
        if rpm >= samples[-1][0]:
            return samples[-1][1]
        for i in range(1, len(samples)):
            r0, t0 = samples[i - 1]
            r1, t1 = samples[i]
            if r0 <= rpm <= r1:
                span = (r1 - r0) or 1.0
                return t0 + (t1 - t0) * (rpm - r0) / span
        return samples[-1][1]

    rpm_min, rpm_max = samples[0][0], samples[-1][0]
    step = (rpm_max - rpm_min) / (target_points - 1)
    torque_curve: list = []
    power_curve: list = []
    for i in range(target_points):
        rpm = rpm_min + step * i
        nm = torque_at(rpm)
        torque_curve.append([round(rpm, 1), round(nm, 3)])
        power_curve.append([round(rpm, 1), round(nm * rpm / 9549.0, 3)])
    return power_curve, torque_curve


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

    # AC draws the showroom graphs from these arrays, not from a filename.
    power_curve, torque_curve = _curve_pairs(car_dir)
    if power_curve:
        ui["powerCurve"] = power_curve
        ui["torqueCurve"] = torque_curve
    else:
        ui.setdefault("powerCurve", [])
        ui.setdefault("torqueCurve", [])

    specs = ui["specs"]
    if "bhp" not in specs and "power" in specs:
        # Derive a numeric bhp so AC can sort by power.
        digits = "".join(ch for ch in str(specs["power"]).split("@")[0] if ch.isdigit())
        if digits:
            specs["bhp"] = int(digits)
    specs.setdefault("weight", specs.get("kerb_weight", "n/a"))
    specs.setdefault("torque", "n/a")
    # AC renders top speed / acceleration only when these are null, not "n/a".
    if specs.get("topspeed") in ("n/a", "", None):
        specs["topspeed"] = None
    if specs.get("acceleration") in ("n/a", "", None):
        specs["acceleration"] = None

    # AC's showroom prints these as strings like "107 bhp" / "1040 kg", and
    # computes the power-to-weight ratio itself.
    bhp = specs.get("bhp")
    if isinstance(bhp, (int, float)):
        specs["bhp"] = f"{int(bhp)} bhp"
    weight_kg = None
    raw_weight = str(specs.get("kerb_weight") or specs.get("weight") or "")
    digits = "".join(ch for ch in raw_weight if ch.isdigit())
    if digits:
        weight_kg = int(digits)
        specs["weight"] = f"{weight_kg} kg"
    if isinstance(bhp, (int, float)) and weight_kg:
        specs["pwratio"] = f"{weight_kg / bhp:.1f} kg/hp"

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


def ensure_upgrade_icon(car_dir: Path) -> bool:
    """AC shows ui/upgrade.png in the showroom; generate a simple one."""
    target = car_dir / "ui" / "upgrade.png"
    if target.exists():
        return False
    # 128x128 with a light "HK" plate so the showroom slot is not blank.
    size = 128
    rows = []
    for y in range(size):
        row = bytearray((0,))
        for x in range(size):
            inside = 24 <= x < size - 24 and 40 <= y < size - 40
            if inside:
                # Simple diagonal band pattern.
                shade = 210 if ((x + y) // 16) % 2 == 0 else 170
                row += bytes((30, 60, shade, 255))
            else:
                row += bytes((0, 0, 0, 0))
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9))
    data += chunk(b"IEND", b"")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def main() -> None:
    total_cars = 0
    total_skins = 0
    for car_dir in sorted(CARS.iterdir()):
        if not car_dir.is_dir() or not car_dir.name.startswith("hk_cat"):
            continue
        ui = ensure_ui(car_dir)
        n = ensure_skins(car_dir, ui)
        icon = ensure_upgrade_icon(car_dir)
        total_cars += 1
        total_skins += n
        curves = len(ui.get("powerCurve") or [])
        print(f"[OK] {car_dir.name}: {n} skins, {curves}-point curves, "
              f"upgrade.png {'new' if icon else 'existing'}")
    print(f"\n{total_cars} cars, {total_skins} skins total")


if __name__ == "__main__":
    main()
