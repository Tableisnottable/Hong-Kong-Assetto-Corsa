"""Choose a destination for any of the six KMB buses from installed OMSI data."""
from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OMSI = Path(r"A:\SteamLibrary\steamapps\common\OMSI 2")
AC_CARS = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa\content\cars")
VEHICLES = OMSI / "Vehicles"


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


def main() -> int:
    # Import here: prepare_kmb_displays shares the HOF reader in this module.
    from prepare_kmb_displays import PROFILES, prepare, route_label

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bus", nargs="?", choices=["all", *PROFILES])
    parser.add_argument("--hof", type=Path, help="OMSI destination file")
    parser.add_argument("--list", action="store_true", help="list HOF destinations without installation")
    parser.add_argument("--output", type=Path, help="local generated files and backups")
    args = parser.parse_args()
    if args.bus is None:
        choices = ["all", *PROFILES]
        for i, family in enumerate(choices, 1):
            print(f"{i}. {family}")
        while True:
            value = input("Choose bus (number or name): ").strip().lower()
            if value.isdigit() and 1 <= int(value) <= len(choices):
                args.bus = choices[int(value) - 1]
                break
            if value in choices:
                args.bus = value
                break
    # One shared full KMB HOF; each family still selects its own display artwork.
    hof = args.hof or VEHICLES / "ADL_E200_KMB_AAU_with_OrangePai/KMB_AllRoutes_Full.hof"
    if not hof.is_file():
        print(f"HOF file not found: {hof}", file=sys.stderr)
        return 2
    entries = read_hof(hof)
    if not entries:
        print(f"No destination entries found in {hof}", file=sys.stderr)
        return 2
    if args.list:
        for item in entries:
            route, destination = route_label(item["destination"], item["route"])
            print(f"{route}\t{destination}\t{';'.join(item['bitmaps'])}")
        return 0
    running = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, check=True)
    if '"acs.exe"' in running.stdout.lower():
        print("Close Assetto Corsa before changing destination skins.", file=sys.stderr)
        return 2
    query = input("Route number (or part of a destination): ").strip()
    matches = [x for x in entries if query.casefold() in
               (" ".join(route_label(x["destination"], x["route"]))).casefold()]
    if not query or not matches:
        print("No matching route found.", file=sys.stderr)
        return 2
    selected = choose(matches, "Choose destination number: ") if len(matches) > 1 else matches[0]
    route, destination = route_label(selected["destination"], selected["route"])
    filename = selected["bitmaps"][0] if selected["bitmaps"] else "__render_from_hof__.bmp"
    routes = [("kmb_custom_route", route, destination, filename)]
    families = list(PROFILES) if args.bus == "all" else [args.bus]
    for family in families:
        car = AC_CARS / PROFILES[family]["id"]
        if not (car / (car.name + ".kn5")).is_file():
            print(f"Converted bus is not installed: {car}", file=sys.stderr)
            return 4
    output = args.output or (Path.home() / "Documents/Assetto Corsa/kmb_tools/displays" /
                            datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    output.mkdir(parents=True, exist_ok=True)
    for family in families:
        car = AC_CARS / PROFILES[family]["id"]
        report = prepare(car, family, routes, output, True)
        warnings = sorted({x["warning"] for x in report["entries"] if x.get("warning")})
        print(f"Updated {car.name}: {route} | {destination} ({report['colour']})")
        for warning in warnings:
            print("  " + warning)
    print("In Content Manager, refresh skins and choose KMB CUSTOM before driving.")
    print("Traffic Planner: rebuild with --skin kmb_custom_route to bake this destination.")
    print(f"Backups and source records: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
