"""Audit installed KMB AI cars and install a selectable Content Manager grid.

Does not start AC, alter race.ini or replace car physics. Writes only a new
grid preset and a local audit report. CM schema: AcTools RaceGridViewModel.cs.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct

import numpy as np
from kn5_tools import Kn5
from repair_omsi_bus_physics import AC, ini, save, world_vertices

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config/kmb_ai_buses.json"


def buses():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["buses"]


def audit_bus(ac, bus):
    car = ac / "content/cars" / bus["id"]
    data = car / "data"
    problems = []
    for rel in (bus["id"] + ".kn5", "collider.kn5", "data/ai.ini", "data/drivetrain.ini",
                "data/power.lut", "data/tyres.ini", "data/engine.ini", "data/suspensions.ini",
                "ui/ui_car.json", "skins/" + bus["skin"]):
        if not (car / rel).exists():
            problems.append("Missing " + rel)
    if problems:
        return {"car": car.name, "errors": problems}
    model = Kn5(car / (car.name + ".kn5"))
    nodes = {n.name: n for _, n in model.root.walk()}
    ai, engine, drive, susp, tyres = [ini(data / (name + ".ini")) for name in
                                     ("ai", "engine", "drivetrain", "suspensions", "tyres")]
    power = np.loadtxt(data / "power.lut", delimiter="|")
    up, down = float(ai["GEARS"]["UP"]), float(ai["GEARS"]["DOWN"])
    limit = float(engine["ENGINE_DATA"]["LIMITER"])
    torque = float(np.interp(up, power[:, 0], power[:, 1]))
    if not (0 < down < up < limit and torque > 0):
        problems.append("AI shifts outside usable torque range")
    count = int(drive["GEARS"]["COUNT"])
    ratios = [float(drive["GEARS"][f"GEAR_{i}"]) for i in range(1, count + 1)]
    if not ratios or any(v <= 0 for v in ratios) or any(a < b for a, b in zip(ratios, ratios[1:])):
        problems.append("Invalid forward gear sequence")
    if float(drive["GEARS"]["FINAL"]) <= 0 or float(drive["GEARS"]["GEAR_R"]) >= 0:
        problems.append("Invalid final/reverse ratio")
    wheels = {}
    wb, cg = float(susp["BASIC"]["WHEELBASE"]), float(susp["BASIC"]["CG_LOCATION"])
    for suffix in ("LF", "RF", "LR", "RR"):
        if "HUB_" + suffix not in nodes or "WHEEL_" + suffix not in nodes:
            problems.append("Missing wheel hierarchy " + suffix)
            continue
        axle = "FRONT" if suffix in ("LF", "RF") else "REAR"
        pos = nodes["HUB_" + suffix].matrix[3, :3]
        expected = np.array([float(susp[axle]["TRACK"]) / 2 * (1 if suffix[0] == "L" else -1),
                             float(susp[axle]["BASEY"]), wb * (1 - cg if axle == "FRONT" else -cg)])
        error = float(abs(pos - expected).max())
        if error > .005:
            problems.append(f"{suffix} pivot mismatch {error:.4f} m")
        wheels[suffix] = {"pivot_error_m": error, "nominal_ground_y_m":
                         float(pos[1] + bus["cg_height"] - float(tyres[axle]["RADIUS"]))}
    for path in data.glob("*.ini"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            value = line.split(";", 1)[0].partition("=")[2].strip()
            if value.lower().endswith(".lut") and not (data / value).is_file():
                problems.append(f"Missing LUT {path.name}: {value}")
    if not list((car / "sfx").glob("*.bank")):
        problems.append("No sound bank")
    hull = Kn5(car / "collider.kn5")
    hull_min = np.concatenate(list(world_vertices(hull.root))).min(0)
    if hull_min[1] + bus["cg_height"] < .1:
        problems.append("Collider too close to nominal road")
    return {"car": car.name, "errors": problems, "ai_upshift_rpm": up,
            "torque_at_shift_nm": torque, "gears": ratios, "wheels": wheels,
            "model_sha256": hashlib.sha256((car / (car.name + ".kn5")).read_bytes()).hexdigest()}


def write_backed_up(path, contents, backup):
    if path.exists() and path.read_bytes() == contents:
        return
    if path.exists():
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)


def align_tracks(ac, registry, backup):
    """Match axle widths to existing hubs; preserve every other suspension value."""
    import subprocess
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"], capture_output=True, text=True, check=True)
    if '"acs.exe"' in result.stdout.lower():
        raise RuntimeError("Close AC before aligning wheel tracks")
    edits = []
    for bus in registry:
        car = ac / "content/cars" / bus["id"]
        model = Kn5(car / (car.name + ".kn5"))
        nodes = {n.name: n for _, n in model.root.walk()}
        path = car / "data/suspensions.ini"
        cp = ini(path)
        changed = False
        for section, left, right in (("FRONT", "LF", "RF"), ("REAR", "LR", "RR")):
            a, b = [nodes["HUB_" + s].matrix[3, :3] for s in (left, right)]
            width = float(a[0] - b[0])
            if abs(a[0] + b[0]) > .002 or abs(a[2] - b[2]) > .002:
                raise ValueError("Asymmetric axle requires manual alignment: " + car.name)
            if abs(width - float(cp[section]["TRACK"])) > .001:
                cp[section]["TRACK"] = f"{width:.8f}"
                edits.append({"car": car.name, "axle": section, "track_m": width})
                changed = True
        if changed:
            dest = backup / car.name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest / path.name)
            save(cp, path)
    return edits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/KMB_AI")
    parser.add_argument("--cm", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "AcTools Content Manager")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--align-tracks", action="store_true", help="Back up and match installed front/rear track widths to their wheel hubs")
    args = parser.parse_args()
    registry = buses()
    backup = args.output / "backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    track_edits = align_tracks(args.ac, registry, backup) if args.align_tracks else []
    checks = [audit_bus(args.ac, bus) for bus in registry]
    args.output.mkdir(parents=True, exist_ok=True)
    result = {"status": "PASS" if all(not c["errors"] for c in checks) else "FAIL", "buses": checks, "track_edits": track_edits,
              "runtime_test": "pending user AI and driving test", "native_ai_layouts": []}
    for path in sorted((args.ac / "content/tracks/route_twisk").rglob("fast_lane.ai")):
        version, count, _, _ = struct.unpack_from("<4i", path.read_bytes())
        if version == 7 and count > 10:
            result["native_ai_layouts"].append(str(path.parent.parent))
    if result["status"] == "PASS":
        grid = {"ModeId": "custom", "FilterValue": None, "CarIds": [b["id"] for b in registry],
                "SkinIds": [b["skin"] for b in registry], "Names": [b["name"] for b in registry],
                "Nationalities": ["Hong Kong"] * len(registry), "OpponentsNumber": len(registry),
                "StartingPosition": len(registry) + 1, "ShuffleCandidates": False,
                "AiLevel": 90, "AiLevelMin": 90, "AiLevelArrangeRandom": 0,
                "AiAggression": 0, "AiAggressionMin": 0, "AiAggressionArrangeRandom": 0}
        payload = json.dumps(grid, indent=2).encode("utf-8")
        name = "KMB - All 6 Buses.cmpreset"
        (args.output / name).write_bytes(payload)
        if args.install:
            dest = args.cm / "Presets/Race Grids" / name
            backup = args.output / "backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            write_backed_up(dest, payload, backup)
            result["installed_preset"] = str(dest)
    (args.output / "native_ai_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "buses": len(checks),
                      "errors": {c["car"]: c["errors"] for c in checks if c["errors"]},
                      "installed_preset": result.get("installed_preset"),
                      "report": str(args.output / "native_ai_validation.json")}, indent=2))
    raise SystemExit(result["status"] != "PASS")


if __name__ == "__main__":
    main()
