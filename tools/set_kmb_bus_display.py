"""Set the E200/E6M AC destination boards from local OMSI HOF and bitmap data."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OMSI = Path(r"A:\SteamLibrary\steamapps\common\OMSI 2")
AC_CARS = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
VEHICLES = OMSI / "Vehicles"
FAMILY = {
    "e200": "kmb_e200_drivable",
    "e6m": "kmb_e6m_drivable",
}
FACES = {
    "front": (0, 0, 416, 128),
    "side": (0, 144, 512, 240),
    "rear": (64, 256, 208, 416),
}


def decode_hof(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp950", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("cp1252", errors="replace")


def read_hof(path: Path) -> list[dict[str, str]]:
    lines = decode_hof(path).splitlines()
    entries: list[dict[str, str]] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().lower() != "[addterminus]":
            i += 1
            continue
        i += 1
        fields: list[str] = []
        while i < len(lines) and not re.fullmatch(r"\s*\[[^]]+\]\s*", lines[i]):
            value = lines[i].strip()
            if value and not value.startswith("#"):
                fields.append(value)
            i += 1
        if len(fields) < 2:
            continue
        route, destination = fields[:2]
        bitmaps = [Path(x.replace("\\", "/")).name for x in fields[2:]
                   if x.lower().endswith(".bmp") and ".." not in Path(x).parts]
        if route.isdigit() or re.fullmatch(r"[A-Za-z0-9-]{1,8}", route):
            entries.append({"route": route, "destination": destination, "bitmaps": bitmaps})
    return entries


def find_assets(vehicle_root: Path, bitmap_names: list[str]) -> Path | None:
    search_roots = [
        OMSI / "Vehicles" / "Anzeigen" / "HANOVER_ORANGE_FULL" / "KMBVC",
        OMSI / "Vehicles" / "Anzeigen" / "HANOVER_WHITE_FULL" / "KMBVC",
        vehicle_root / "Texture",
        vehicle_root / "texture",
    ]
    for name in bitmap_names:
        for root in search_roots:
            candidate = root / name
            if candidate.is_file():
                return candidate
    return None


def choose(items: list[dict[str, str]], title: str) -> dict[str, str]:
    for n, item in enumerate(items, 1):
        print(f"{n:>3}. {item['route']:<8} {item['destination']}")
    while True:
        value = input(title).strip()
        if value.isdigit() and 1 <= int(value) <= len(items):
            return items[int(value) - 1]
        matches = [x for x in items if value.casefold() in (x["route"] + " " + x["destination"]).casefold()]
        if len(matches) == 1:
            return matches[0]
        if matches:
            items = matches
            print(f"{len(items)} matches:")
            for n, item in enumerate(items, 1):
                print(f"{n:>3}. {item['route']:<8} {item['destination']}")
        else:
            print("No matching route or destination. Enter a displayed number or search text.")


def display_route(destination: str, fallback: str) -> tuple[str, str]:
    match = re.match(r"^([A-Za-z0-9]+)\s+(.+)$", destination.strip())
    return (match.group(1), match.group(2)) if match else (fallback, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bus", choices=FAMILY, help="bus to update")
    parser.add_argument("--hof", type=Path, help="HOF file; defaults to this bus family's full KMB route list")
    parser.add_argument("--list", action="store_true", help="print available route destinations without changing files")
    args = parser.parse_args()

    vehicle_root = VEHICLES / {
        "e200": "ADL_E200_KMB_AAU_with_OrangePai",
        "e6m": "ADL_E500MMC_KMB_E6M",
    }[args.bus]
    hof = args.hof or (vehicle_root / "KMB_AllRoutes_Full.hof" if args.bus == "e200"
                       else vehicle_root / "model" / "KMB_AllRoutes_Full.hof")
    if not hof.is_file():
        print(f"HOF file not found: {hof}", file=sys.stderr)
        return 2
    entries = read_hof(hof)
    if not entries:
        print(f"No destination entries found in {hof}", file=sys.stderr)
        return 2
    if args.list:
        for item in entries:
            print(f"{item['route']}\t{item['destination']}\t{';'.join(item['bitmaps'])}")
        return 0

    query = input("Route number (or part of a destination): ").strip()
    matches = [x for x in entries if query.casefold() in (x["route"] + " " + x["destination"]).casefold()]
    if not matches:
        print("No matching route found.", file=sys.stderr)
        return 2
    selected = choose(matches, "Choose destination number: ") if len(matches) > 1 else matches[0]
    source = find_assets(vehicle_root, selected["bitmaps"])
    if source is None:
        print("No matching original OMSI bitmap was found for this destination.", file=sys.stderr)
        print("This HOF entry may use script-generated or non-Hanover artwork.", file=sys.stderr)
        return 3

    car = AC_CARS / FAMILY[args.bus]
    if not (car / (FAMILY[args.bus] + ".kn5")).is_file():
        print(f"Converted bus is not installed: {car}", file=sys.stderr)
        return 4
    skin = car / "skins" / "kmb_custom_route"
    skin.mkdir(parents=True, exist_ok=True)
    seed = car / "skins" / "0_kmb"
    for name in ("skin.ini", "livery.png"):
        if (seed / name).is_file():
            shutil.copy2(seed / name, skin / name)

    source_image = Image.open(source).convert("RGB")
    for face, crop in FACES.items():
        panel = source_image.crop(crop)
        if panel.width == 0 or panel.height == 0:
            raise ValueError(f"Invalid {face} board crop in {source}")
        # Match the sign panels already installed in the E200 and E6M KN5s.
        size = {"front": (1024, 196), "side": (1024, 544), "rear": (1024, 612)}[face]
        fitted = ImageOps.contain(panel, size, Image.Resampling.NEAREST)
        canvas = Image.new("RGB", size, "black")
        canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
        canvas.save(skin / f"kmb_destination_{face}.dds", format="DDS", pixel_format="DXT5")

    shown_route, shown_destination = display_route(selected["destination"], selected["route"])
    metadata = {"skinname": f"KMB CUSTOM | {shown_route} | {shown_destination}",
                "drivername": "", "country": "Hong Kong", "number": shown_route}
    (skin / "ui_skin.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {car.name} display: {shown_route} | {shown_destination}")
    print(f"Source: {source}")
    print("In Content Manager, refresh the car skins and select the KMB CUSTOM skin before driving.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
