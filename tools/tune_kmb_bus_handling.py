"""Apply OMSI-derived steering and automatic shift timing to installed KMB cars."""
from __future__ import annotations

import argparse
import configparser
import datetime
import json
import math
from pathlib import Path
import shutil

from repair_omsi_bus_physics import AC, Kn5, ini, numbers, save, source_spec

OMSI = Path(r"A:/SteamLibrary/steamapps/common/OMSI 2/Vehicles")
FLEET = {
    "kmb_e200_drivable": ("ADL_E200_KMB_AAU_with_OrangePai", "AAU.bus"),
    "kmb_e6m_drivable": ("ADL_E500MMC_KMB_E6M", "E6M_Grey_White.bus"),
    "kmb_atenu_drivable": ("ADL_E500MMC_KMB_ATENU", "ATENU.bus"),
    "kmb_atee_drivable": ("ADL_Enviro500_KMB_ATEE_WV820", "ATEE_Ex_LWB.bus"),
    "kmb_scania_k230ub_drivable": ("Scania_K230UB_KMB_ASB_ASC_4479", "ASB_Gorba.bus"),
    "kmb_dennis_dragon_9m_drivable": (
        "Dennis_Dragon 9.9M_KMB_ADS186_235", "Dennis_Dragon_ADS186-235_NPHxMB.bus"
    ),
}


def tune(car_id: str, install: bool) -> dict:
    source_dir, bus_file = FLEET[car_id]
    source = OMSI / source_dir
    bus_path = source / bus_file
    spec = source_spec(source, bus_file)
    bus_text = bus_path.read_text(encoding="cp1252", errors="replace")
    inverse_radius = numbers(bus_text, "inv_min_turnradius")[0]
    car = AC / "content/cars" / car_id
    data = car / "data"
    car_ini = ini(data / "car.ini")
    suspension = ini(data / "suspensions.ini")
    drivetrain = ini(data / "drivetrain.ini")
    steer_ratio = abs(float(car_ini["CONTROLS"]["STEER_RATIO"]))
    wheelbase = float(suspension["BASIC"]["WHEELBASE"])
    max_roadwheel_angle = math.degrees(math.atan(inverse_radius * wheelbase))
    steer_lock = round(steer_ratio * max_roadwheel_angle)
    gearbox = spec["gear_constants"]
    shift_seconds = float(gearbox.get("antrieb_gangwahlzeit", 0.5))
    shift_ms = round(min(0.8, max(0.45, shift_seconds)) * 1000)
    model = Kn5(car / f"{car_id}.kn5")
    model_nodes = [node for _, node in model.root.walk()]
    node_names = {node.name for node in model_nodes}
    mirror_path = data / "mirrors.ini"
    mirror_config = ini(mirror_path)
    mirror_names = [
        node.name for node in model_nodes
        if node.kind == 2 and node.material_id >= 0
        and any(Path(tex["texture"]).stem.casefold().startswith("reflexion")
                for tex in model.materials[node.material_id]["maps"])
    ]
    if not mirror_names:
        raise ValueError(f"No OMSI reflection meshes found in {car_id}")
    configured_mirrors = [mirror_config[section].get("NAME", "")
                          for section in mirror_config.sections()]
    mirror_repair = any(name not in node_names for name in configured_mirrors)
    changed = {
        "data/car.ini": car_ini,
        "data/drivetrain.ini": drivetrain,
    }
    if mirror_repair:
        mirror_config.clear()
        for index, name in enumerate(mirror_names):
            mirror_config[f"MIRROR_{index}"] = {"NAME": name}
        changed["data/mirrors.ini"] = mirror_config
    car_ini["CONTROLS"]["STEER_LOCK"] = str(steer_lock)
    drivetrain["GEARBOX"]["CHANGE_UP_TIME"] = str(shift_ms)
    drivetrain["GEARBOX"]["CHANGE_DN_TIME"] = str(shift_ms + 100)
    drivetrain["GEARBOX"]["AUTO_CUTOFF_TIME"] = str(shift_ms)
    drivetrain["AUTO_SHIFTER"]["GAS_CUTOFF_TIME"] = f"{shift_seconds:.2f}"

    record = {
        "car": car_id,
        "source_bus": str(bus_path),
        "source_engine": spec["engine_file"],
        "source_gearbox": spec["gearbox_file"],
        "inverse_min_turn_radius": inverse_radius,
        "wheelbase_m": wheelbase,
        "max_roadwheel_angle_deg": round(max_roadwheel_angle, 2),
        "steering_ratio": steer_ratio,
        "steer_lock_deg": steer_lock,
        "shift_selection_time_s": shift_seconds,
        "ac_upshift_ms": shift_ms,
        "ac_downshift_ms": shift_ms + 100,
        "mirror_meshes": mirror_names,
        "mirror_repair_needed": mirror_repair,
        "runtime_test": "pending user drive",
    }
    if not install:
        return record

    backup_root = Path(__file__).resolve().parents[1] / "outputs" / "kmb_handling_backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S") / car_id
    for relative, cp in changed.items():
        target = car / relative
        if not target.is_file():
            raise FileNotFoundError(target)
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        save(cp, target)
    record["backup"] = str(backup_root)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true", help="Back up and update all six installed bus configs")
    args = parser.parse_args()
    if args.install:
        import subprocess

        tasks = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"],
            capture_output=True, text=True, check=True,
        )
        if '"acs.exe"' in tasks.stdout.lower():
            raise RuntimeError("Close Assetto Corsa before installing handling changes")
    results = [tune(car, args.install) for car in FLEET]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
