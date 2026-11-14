"""Install fixed Assetto Corsa setup sliders from each KMB car's drivetrain.ini."""
from __future__ import annotations

import argparse
import configparser
import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess

from repair_omsi_bus_physics import AC
from tune_kmb_bus_handling import FLEET


BEGIN = "; KMB_FIXED_GEAR_SETUP_BEGIN"
END = "; KMB_FIXED_GEAR_SETUP_END"


def read_ini(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str.upper
    cp.read(path, encoding="utf-8-sig")
    return cp


def render_setup(setup_path: Path, gear_count: int) -> str:
    source = setup_path.read_text(encoding="utf-8-sig") if setup_path.exists() else ""
    source = re.sub(r"(?ms)^" + re.escape(BEGIN) + r"\s*\n.*?^" + re.escape(END) + r"\s*\n?", "", source)
    blocks = [BEGIN, "[GEARS]", "USE_GEARSET=0", ""]
    for gear in range(1, gear_count + 1):
        blocks.extend((f"[GEAR_{gear}]", f"RATIOS=kmb_gear_{gear}.rto", f"NAME=Gear {gear}",
                       "POS_X=0", f"POS_Y={gear - 1}", "HELP=HELP_REAR_GEAR", ""))
    blocks.extend(("[FINAL_GEAR_RATIO]", "RATIOS=kmb_final.rto", "NAME=Final Gear Ratio",
                   "POS_X=1", "POS_Y=0", "HELP=HELP_REAR_GEAR", END, ""))
    return source.rstrip() + "\n\n" + "\n".join(blocks)


def install(car_id: str, ac_root: Path, backup_root: Path, apply: bool) -> dict:
    car = ac_root / "content/cars" / car_id
    data = car / "data"
    drivetrain = read_ini(data / "drivetrain.ini")
    gears = drivetrain["GEARS"]
    count = int(gears["COUNT"])
    ratios = {f"kmb_gear_{i}.rto": float(gears[f"GEAR_{i}"]) for i in range(1, count + 1)}
    ratios["kmb_final.rto"] = float(gears["FINAL"])
    setup_path = data / "setup.ini"
    setup_text = render_setup(setup_path, count)
    changes = {setup_path: setup_text.encode("utf-8")}
    changes.update({data / name: f"{ratio:.8g}|{ratio:.8g}\n".encode("ascii")
                    for name, ratio in ratios.items()})
    changed = [path for path, content in changes.items()
               if not path.exists() or path.read_bytes() != content]
    if apply:
        for path in changed:
            backup = backup_root / car_id / path.name
            if path.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(changes[path])
    return {"car": car_id, "forward_gears": count, "ratios": ratios,
            "changed_files": [str(p) for p in changed]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--install", action="store_true", help="Back up and update all six installed KMB cars")
    args = parser.parse_args()
    if args.install:
        tasks = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"],
                               capture_output=True, text=True, check=True)
        if '"acs.exe"' in tasks.stdout.lower():
            raise RuntimeError("Close AC before installing gear setup files")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = Path(__file__).resolve().parents[1] / "outputs" / "kmb_gear_setup_backups" / stamp
    records = [install(car_id, args.ac, backup_root, args.install) for car_id in FLEET]
    report = {"status": "INSTALLED" if args.install else "PREVIEW", "cars": records,
              "runtime_test": "pending user drive"}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
