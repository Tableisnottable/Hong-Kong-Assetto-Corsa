"""Stage OMSI-derived powertrain, axle and steering settings for all KMB cars.

The default run writes only to outputs/KMB_REALISM. --install requires AC to be
closed, rechecks staged and installed hashes, and backs up every replaced INI.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

import numpy as np

from prepare_kmb_ai_grid import ROOT
from repair_omsi_bus_physics import (
    AC, apply_source_powertrain, apply_source_suspension,
    ini, numbers, save, set_values, source_spec,
)
from tune_kmb_bus_handling import FLEET


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def family_for(source_dir: str) -> str:
    if source_dir.startswith("Dennis_Dragon"):
        return "dragon"
    if source_dir.startswith("Scania_"):
        return "scania"
    return "standard"


def ensure_closed() -> None:
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV", "/NH"],
                            capture_output=True, text=True, check=True)
    if any(line.lstrip().lower().startswith('"acs.exe"') for line in result.stdout.splitlines()):
        raise RuntimeError("Close Assetto Corsa before installing KMB physics settings")


def prepare_car(ac_root: Path, omsi_root: Path, car_id: str, source_dir: str,
                bus_file: str, out_root: Path) -> dict:
    car = ac_root / "content/cars" / car_id
    source = omsi_root / source_dir
    spec = source_spec(source, bus_file)
    data = car / "data"
    names = ("car.ini", "engine.ini", "drivetrain.ini", "suspensions.ini", "tyres.ini")
    configs = {name: ini(data / name) for name in names}
    original = {name: sha256(data / name) for name in names}

    # AC's tire/wheel geometry stays mesh-measured; update only source-supported
    # axle spring/damper data and the source mass reference.
    points = np.loadtxt(data / "power.lut", delimiter="|")
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError(f"Invalid power curve: {car_id}")
    curve_error = max(abs(float(np.interp(rpm, points[:, 0], points[:, 1])) - torque)
                      for rpm, torque in spec["curve"])
    if curve_error > 1.0:
        raise ValueError(f"Installed torque curve differs from OMSI source by {curve_error:.1f} Nm: {car_id}")

    source_mass = round(spec["mass"])
    set_values(configs["car.ini"], "BASIC", {"TOTALMASS": source_mass})
    bus_text = (source / bus_file).read_text(encoding="cp1252", errors="replace")
    inverse_radius = numbers(bus_text, "inv_min_turnradius")[0]
    wheelbase = float(configs["suspensions.ini"]["BASIC"]["WHEELBASE"])
    steering_ratio = abs(float(configs["car.ini"]["CONTROLS"]["STEER_RATIO"]))
    roadwheel_degrees = math.degrees(math.atan(inverse_radius * wheelbase))
    steer_lock = round(steering_ratio * roadwheel_degrees)
    set_values(configs["car.ini"], "CONTROLS", {"STEER_LOCK": steer_lock})

    family = family_for(source_dir)
    front_radius = float(configs["tyres.ini"]["FRONT"]["RADIUS"])
    rear_radius = float(configs["tyres.ini"]["REAR"]["RADIUS"])
    contact_loads = apply_source_suspension(configs["suspensions.ini"], configs["tyres.ini"], spec,
                                            family, source_mass, front_radius, rear_radius)
    powertrain = apply_source_powertrain(configs["engine.ini"], configs["drivetrain.ini"], spec, family)

    destination = out_root / "content/cars" / car_id / "data"
    destination.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, cp in configs.items():
        staged = destination / name
        save(cp, staged)
        files[f"content/cars/{car_id}/data/{name}"] = {
            "sha256": sha256(staged), "original_sha256": original[name],
        }

    source_paths = [Path(spec["engine_file"]), Path(spec["gearbox_file"]), source / bus_file]
    return {
        "car": car_id, "source_bus": str(source / bus_file),
        "source_mass_kg": source_mass, "source_cg_height_m": spec["cg_height"],
        "source_engine_sha256": sha256(source_paths[0]),
        "source_gearbox_sha256": sha256(source_paths[1]),
        "source_bus_sha256": sha256(source_paths[2]),
        "max_torque_curve_error_nm": round(curve_error, 5),
        "engine": powertrain, "steering": {"inverse_turn_radius": inverse_radius,
            "wheelbase_m": wheelbase, "roadwheel_angle_deg": round(roadwheel_degrees, 3),
            "steer_ratio": steering_ratio, "steer_lock": steer_lock},
        "suspension": {section: {key: configs["suspensions.ini"][section][key]
            for key in ("SPRING_RATE", "DAMP_BUMP", "DAMP_REBOUND", "ROD_LENGTH")}
            for section in ("FRONT", "REAR")},
        "static_contact_load_estimate": contact_loads,
        "source_axles": spec["axles"], "files": files,
        "limitations": ["AC physics still has four tire contact points; extra axles remain a visual/script approximation."],
    }


def install_staged(ac_root: Path, run: Path, report: dict) -> None:
    ensure_closed()
    for bus in report["buses"]:
        for relative, item in bus["files"].items():
            staged, installed = run / relative, ac_root / relative
            if not staged.is_file() or sha256(staged) != item["sha256"]:
                raise ValueError("Staged file changed; refusing install: " + str(staged))
            if not installed.is_file() or sha256(installed) != item["original_sha256"]:
                raise ValueError("Installed file changed since staging; make a fresh stage: " + str(installed))
    backup_root = run / "backups"
    for bus in report["buses"]:
        for relative in bus["files"]:
            staged, installed = run / relative, ac_root / relative
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(installed, backup)
            shutil.copy2(staged, installed)
            if sha256(installed) != bus["files"][relative]["sha256"]:
                raise ValueError("Installed hash mismatch: " + str(installed))
    report["installed"] = True
    report["installed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    report["backup_directory"] = str(backup_root)
    (run / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--omsi", type=Path, default=Path(r"A:/SteamLibrary/steamapps/common/OMSI 2/Vehicles"))
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/KMB_REALISM")
    parser.add_argument("--resume", type=Path, help="Install a previously staged run")
    parser.add_argument("--install", action="store_true", help="Install after verifying AC is closed")
    args = parser.parse_args()
    if args.install:
        ensure_closed()
    run = args.resume or args.output / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.resume:
        report_path = run / "validation.json"
        if not report_path.is_file():
            raise FileNotFoundError(report_path)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("status") != "PASS" or report.get("installed"):
            raise ValueError("Only a passing, not-yet-installed stage can be resumed")
    else:
        buses = []
        for car_id, (source_dir, bus_file) in FLEET.items():
            buses.append(prepare_car(args.ac, args.omsi, car_id, source_dir, bus_file, run))
        report = {"status": "PASS", "installed": False, "buses": buses,
                  "scope": "six OMSI-derived AC bus configurations",
                  "runtime": "pending user drive; Assetto Corsa is not launched by this tool"}
        run.mkdir(parents=True, exist_ok=True)
        (run / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.install:
        install_staged(args.ac, run, report)
    print(json.dumps({"status": report["status"], "installed": report.get("installed", False),
                      "run": str(run), "buses": [b["car"] for b in report["buses"]]}, indent=2))


if __name__ == "__main__":
    main()
