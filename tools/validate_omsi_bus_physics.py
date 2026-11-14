"""Read-only geometry/physics audit for a repaired local OMSI bus package.

Checks the installed files too when road_contact_repair.json records an install.
Does not launch Assetto Corsa or claim that offline checks verify driving.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from kn5_tools import Kn5
from repair_omsi_bus_physics import ini, world_vertices


def audit(package):
    report = json.loads((package / "road_contact_repair.json").read_text())
    car = package / "content/cars" / report["car_id"]
    model = Kn5(car / (car.name + ".kn5"))
    nodes = {node.name: node for _, node in model.root.walk()}
    data = car / "data"
    susp, tyres, drive, engine, car_ini = [ini(data / (name + ".ini"))
        for name in ("suspensions", "tyres", "drivetrain", "engine", "car")]
    errors, wheel_results = [], {}
    wheelbase = float(susp["BASIC"]["WHEELBASE"])
    distribution = float(susp["BASIC"]["CG_LOCATION"])
    cg_height = report["source_cg_height"]
    for suffix in ("LF", "RF", "LR", "RR"):
        axle = "FRONT" if suffix in ("LF", "RF") else "REAR"
        left = suffix.startswith("L")
        expected = np.array([float(susp[axle]["TRACK"]) / 2 * (1 if left else -1),
                             float(susp[axle]["BASEY"]),
                             wheelbase * (1 - distribution if axle == "FRONT" else -distribution)])
        actual = nodes["HUB_" + suffix].matrix[3, :3]
        error = float(np.max(np.abs(actual - expected)))
        points = np.concatenate(list(world_vertices(nodes["WHEEL_" + suffix])))
        radius = float(np.linalg.norm(points[:, 1:3], axis=1).max())
        physics_radius = float(tyres[axle]["RADIUS"])
        contact = actual[1] + cg_height - physics_radius
        if error > .001:
            errors.append(f"{suffix} pivot differs from physics by {error:.6f} m")
        if abs(radius - physics_radius) > .001:
            errors.append(f"{suffix} tire radius differs from mesh by {radius - physics_radius:.6f} m")
        if abs(contact) > .01:
            errors.append(f"{suffix} nominal contact differs from source ground by {contact:.6f} m")
        wheel_results[suffix] = {"pivot_error_m": error, "visual_radius_m": radius,
                                  "physical_radius_m": physics_radius, "nominal_contact_y_m": float(contact)}
    collider = Kn5(car / "collider.kn5")
    hull = np.concatenate(list(world_vertices(collider.root)))
    clearance = float(hull[:, 1].min() + cg_height)
    if clearance < .25:
        errors.append(f"Hull is below its intended ground clearance: {clearance}")
    graphics_offset = list(map(float, car_ini["BASIC"]["GRAPHICS_OFFSET"].split(",")))
    if graphics_offset != [0, 0, 0]:
        errors.append("Unexpected graphics offset on a normalized model")
    for path in data.glob("*.ini"):
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.split(";", 1)[0].strip()
            if "=" in line:
                value = line.split("=", 1)[1].strip()
                if value.lower().endswith(".lut") and not (data / value).is_file():
                    errors.append(f"Missing LUT {path.name}: {value}")
    up, limit = float(drive["AUTO_SHIFTER"]["UP"]), float(engine["ENGINE_DATA"]["LIMITER"])
    curve = np.loadtxt(data / "power.lut", delimiter="|")
    torque_at_shift = float(np.interp(up, curve[:, 0], curve[:, 1]))
    if not (1000 < up < limit and torque_at_shift > 0):
        errors.append("Automatic upshift occurs outside usable engine torque")
    if int(drive["GEARS"]["COUNT"]) != 6 or float(drive["GEARS"]["GEAR_6"]) <= 0:
        errors.append("Six-speed gearbox is incomplete")
    for rel, digest in report.get("installed_sha256", {}).items():
        dest = Path(report["installed"]) / rel
        if not dest.is_file() or hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
            errors.append(f"Installed hash mismatch: {dest}")
    result = {"status": "PASS" if not errors else "FAIL", "car": car.name,
              "errors": errors, "wheels": wheel_results, "nominal_hull_clearance_m": clearance,
              "torque_at_auto_shift_nm": torque_at_shift,
              "runtime_verification": "pending user drive; nominal contact excludes dynamic tire deflection"}
    (package / "road_contact_validation.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packages", type=Path, nargs="+")
    args = parser.parse_args()
    results = [audit(package) for package in args.packages]
    print(json.dumps(results, indent=2))
    raise SystemExit(int(any(result["errors"] for result in results)))
