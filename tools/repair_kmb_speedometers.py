"""Install OMSI-calibrated speedometer curves for the six local KMB cars."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AC = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa")
PACKAGE_ROOT = Path(r"C:\Users\Table\Documents\Codex\2026-11-13\i-x20\outputs")
BACKUP_ROOT = Path(r"C:\Users\Table\Documents\Codex\backups\kmb_speedometers")

OMSI_CURVE = tuple((float(x), float(y)) for x, y in [
    (0, 0), (5, 0), (10, 7), (20, 27), (30, 52), (40, 74), (50, 99),
    (60, 112), (70, 136), (80, 156), (90, 175), (100, 200), (110, 229), (120, 252),
])
DRAGON_CURVE = tuple((float(x), float(y)) for x, y in [
    (0, 0), (5, 0), (10, 7), (20, 30), (30, 52), (40, 74), (50, 95),
    (60, 115), (70, 135), (80, 162), (90, 185), (100, 208), (110, 229), (120, 252),
])
SCANIA_CURVE = tuple((float(x), float(y * 248)) for x, y in [(0, 0), (20, .05), (110, 1)])

BUSES = {
    "kmb_e200_drivable": ("E200", OMSI_CURVE, "E200_playable"),
    "kmb_e6m_drivable": ("E6M", OMSI_CURVE, "E6M_playable"),
    "kmb_atenu_drivable": ("ATENU", OMSI_CURVE, "ATENU_playable"),
    "kmb_atee_drivable": ("ATEE", OMSI_CURVE, "ATEE_playable"),
    "kmb_dennis_dragon_9m_drivable": ("Dragon", DRAGON_CURVE, "DRAGON_playable"),
    "kmb_scania_k230ub_drivable": ("Scania", SCANIA_CURVE, "SCANIA_playable"),
}
LUA_GAUGE_CARS = {"kmb_e200_drivable", "kmb_e6m_drivable"}


def interpolate(points: tuple[tuple[float, float], ...], speed: float) -> float:
    if speed <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if speed <= x1:
            return y0 + (y1 - y0) * (speed - x0) / (x1 - x0)
    return points[-1][1]


def curve_text(points: tuple[tuple[float, float], ...]) -> str:
    return "".join(f"{x:g}|{y:.6f}\n" for x, y in points)


def destinations(ac_root: Path, source_root: Path, include_source: bool):
    for car_id, (_, curve, package_name) in BUSES.items():
        installed = ac_root / "content/cars" / car_id
        yield car_id, curve, installed / "data/analog_speed_curve.lut", "installed"
        binding = installed / "extension/cockpit_bindings.json"
        if binding.is_file():
            yield car_id, curve, binding, "installed-binding"
        cockpit = installed / "extension/cockpit.lua"
        if car_id in LUA_GAUGE_CARS and cockpit.is_file():
            yield car_id, curve, cockpit, "installed-cockpit"
        if not include_source:
            continue
        if car_id == "kmb_e200_drivable":
            source_car = source_root / "projects/kmb_e200_playable/content/cars" / car_id
        elif car_id == "kmb_e6m_drivable":
            source_car = source_root / "projects/kmb_e6m_playable/content/cars" / car_id
        else:
            source_car = PACKAGE_ROOT / package_name / "content/cars" / car_id
        yield car_id, curve, source_car / "data/analog_speed_curve.lut", "source"
        source_binding = source_car / "extension/cockpit_bindings.json"
        if source_binding.is_file():
            yield car_id, curve, source_binding, "source-binding"
        source_cockpit = source_car / "extension/cockpit.lua"
        if source_cockpit.is_file():
            yield car_id, curve, source_cockpit, "source-cockpit"


def updated_bytes(path: Path, curve: tuple[tuple[float, float], ...]) -> bytes:
    if path.name == "analog_speed_curve.lut":
        return curve_text(curve).encode("ascii")
    if path.name == "cockpit.lua":
        source = path.read_bytes()
        match = re.search(rb'(\["speedCurve"\]=)(\{\{.*?\}\})', source)
        if match is None:
            raise ValueError(f"Expected one embedded speedCurve in {path}")
        existing_curve = tuple(
            (float(x), float(y))
            for x, y in re.findall(rb"\{([-+\d.eE]+),([-+\d.eE]+)\}", match.group(2))
        )
        if existing_curve == curve:
            return source
        lua_curve = "{{" + "},{".join(f"{x!r},{y!r}" for x, y in curve) + "}}"
        return source[:match.start(2)] + lua_curve.encode("ascii") + source[match.end(2):]
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["car"] = BUSES[path.parent.parent.name][0]
    data["speedCurve"] = [[x, y] for x, y in curve]
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def ac_is_running() -> bool:
    result = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Unable to check whether acs.exe is running: {result.stderr.strip()}")
    return any(line.lstrip().lower().startswith('"acs.exe"') for line in result.stdout.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac-root", type=Path, default=AC)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--no-source", action="store_true", help="update only the installed AC cars")
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing")
    parser.add_argument("--backup-root", type=Path, default=BACKUP_ROOT)
    args = parser.parse_args()

    if not args.dry_run and ac_is_running():
        raise SystemExit("Assetto Corsa (acs.exe) is running; close it before installing speedometer files.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    changes = []
    for car_id, curve, path, kind in destinations(args.ac_root, args.source_root, not args.no_source):
        if not path.is_file():
            if kind.startswith("source"):
                print(f"SKIP missing source: {path}")
                continue
            raise FileNotFoundError(path)
        updated = updated_bytes(path, curve)
        original = path.read_bytes()
        if original == updated:
            continue
        changes.append((car_id, path, kind, original, updated))

    for car_id, path, kind, original, updated in changes:
        print(f"{kind}: {path}")
        if args.dry_run:
            continue
        if kind.startswith("installed"):
            relative = Path(car_id) / path.relative_to(args.ac_root / "content/cars" / car_id)
            backup = args.backup_root / timestamp / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
        path.write_bytes(updated)
    print(f"{len(changes)} file(s) {'would change' if args.dry_run else 'updated'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
