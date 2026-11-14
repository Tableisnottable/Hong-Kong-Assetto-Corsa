"""Align converted OMSI buses with AC's CG origin and repair driving data.

Only local converted packages are changed. OMSI sources are read as data.
Run with a package directory; --install also updates the installed car with backups.
"""
from __future__ import annotations

import argparse
import configparser
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

import numpy as np
from kn5_tools import Kn5, Node

AC = Path(r"A:/SteamLibrary/steamapps/common/assettocorsa")


def numbers(text, tag, count=1):
    match = re.search(r"(?m)^\[" + re.escape(tag) + r"\]\s*\r?\n", text)
    if not match:
        raise ValueError(f"Missing OMSI [{tag}]")
    values = text[match.end():].splitlines()[:count]
    return [float(v.strip()) for v in values]


def constants(text):
    return {name.strip(): float(value) for name, value in re.findall(
        r"(?m)^\[const\]\s*\r?\n([^\r\n]+)\r?\n\s*([-+0-9.eE]+)", text)}


def source_spec(source, bus):
    text = (source / bus).read_text(encoding="cp1252", errors="replace")
    match = re.search(r"(?m)^\[constfile\]\s*\r?\n(\d+)\s*\r?\n", text)
    if not match:
        raise ValueError("OMSI bus has no active constant-file list")
    paths = [source / p.strip().replace("\\", "/")
             for p in text[match.end():].splitlines()[:int(match[1])]]
    engine = next(p for p in paths if p.name.lower().startswith("engine_constfile"))
    gearbox = next(p for p in paths if p.name.lower().startswith(("antrieb_constfile", "gearbox_constfile")))
    eng_text = engine.read_text(encoding="cp1252", errors="replace")
    gear_text = gearbox.read_text(encoding="cp1252", errors="replace")
    match = re.search(r"(?ms)^\[newcurve\]\s*\r?\nengine_M_maxThrottle\s*(.*?)(?=^\[newcurve\]|\Z)", eng_text)
    if not match:
        raise ValueError(f"No engine torque curve in {engine}")
    curve = [(float(a), float(b)) for a, b in re.findall(
        r"(?m)^\[pnt\]\s*\r?\n\s*([-+0-9.]+)\s*\r?\n\s*([-+0-9.]+)", match[1])]
    if len(curve) < 4 or any(a[0] >= b[0] for a, b in zip(curve, curve[1:])):
        raise ValueError("Torque curve must have increasing RPM points")
    axle_blocks = re.split(r"(?m)^\[newachse\]\s*$", text)[1:]
    axles = []
    for block in axle_blocks:
        values = {k: float(v) for k, v in re.findall(
            r"(?m)^(achse_\w+)\s*\r?\n\s*([-+0-9.]+)", block)}
        if "achse_feder" in values:
            axles.append(values)
    cameras = [list(map(float, v)) for v in re.findall(
        r"(?m)^\[add_camera_driver\]\s*\r?\n" + r"\s*([-+0-9.]+)\s*\r?\n" * 7, text)]
    camera = next((v for v in cameras if abs(v[5]) < 1), None)
    return {"mass": numbers(text, "mass")[0] * 1000,
            "cg_height": numbers(text, "schwerpunkt")[0],
            "width": numbers(text, "boundingbox", 3)[0],
            "curve": curve, "engine_constants": constants(eng_text),
            "gear_constants": constants(gear_text), "axles": axles, "camera": camera,
            "engine_file": str(engine), "gearbox_file": str(gearbox)}


def ini(path):
    cp = configparser.ConfigParser(interpolation=None, strict=False, inline_comment_prefixes=(";",))
    cp.optionxform = str
    cp.read(path, encoding="utf-8-sig")
    return cp


def save(cp, path):
    with path.open("w", encoding="utf-8") as out:
        cp.write(out, space_around_delimiters=False)


def set_values(cp, section, values):
    if not cp.has_section(section):
        cp.add_section(section)
    for key, value in values.items():
        cp[section][key] = str(value)


def bounds(node):
    vertices = node.vertices[:, :3]
    center = (vertices.min(0) + vertices.max(0)) / 2
    offset = node.vertex_offset + node.vertex_count * node.vertex_stride + 4 + node.index_count * 2 + 16
    struct.pack_into("<4f", node.payload, offset, *center, float(np.linalg.norm(vertices - center, axis=1).max()))


def world_vertices(node, parent=np.eye(4)):
    world = node.matrix @ parent if node.kind == 1 else parent
    if node.kind == 2:
        yield node.vertices[:, :3] @ world[:3, :3] + world[3, :3]
    for child in node.children:
        yield from world_vertices(child, world)


def repair(package, ac=AC, install=False):
    package = Path(package).resolve()
    report = json.loads((package / "build_report.json").read_text(encoding="utf-8"))
    family = report["family"]
    bus_names = {"atenu": "ATENU.bus", "atee": "ATEE_Ex_LWB.bus", "scania": "ASB_Gorba.bus",
                 "dragon": "Dennis_Dragon_ADS186-235_NPHxMB.bus"}
    if family not in bus_names:
        raise ValueError("Unsupported OMSI family")
    spec = source_spec(Path(report["source"]), bus_names[family])
    car = package / "content/cars" / report["car_id"]
    data = car / "data"
    model_path = car / (car.name + ".kn5")
    model = Kn5(model_path)
    nodes = {node.name: node for _, node in model.root.walk()}
    centers = {k: np.array(v, dtype=float) for k, v in report["wheel_centers"].items()}
    # Earlier builds mistook the Dragon's intermediate axle for its driven axle.
    # Swap the hierarchy without moving any mesh in the source coordinate frame.
    remapped = family == "dragon" and report.get("axle_mapping") != "rear driven; intermediate visual"
    if remapped:
        for suffix, tag in (("LR", "TAG_L"), ("RR", "TAG_R")):
            native, visual = nodes["HUB_" + suffix], nodes["OMSI_TAG_" + tag]
            native.name = "OMSI_TAG_" + tag
            native.children = nodes["WHEEL_" + suffix].children
            visual.name = "HUB_" + suffix
            visual.children = [Node.dummy("SUSP_" + suffix), Node.dummy("WHEEL_" + suffix, visual.children)]
            centers[suffix], centers[tag] = centers[tag], centers[suffix]
        nodes = {node.name: node for _, node in model.root.walk()}
    shift = np.array([(centers["LF"][0] + centers["RF"][0]) / 2, spec["cg_height"],
                      (centers["LF"][2] + centers["LR"][2]) / 2])
    delta = nodes["HUB_LF"].matrix[3, :3] - (centers["LF"] - shift)
    # KN5 matrices are float32; do not accumulate sub-micron rounding on repeats.
    delta[np.abs(delta) < 1e-6] = 0
    for suffix in ("LF", "RF", "LR", "RR"):
        actual = nodes["HUB_" + suffix].matrix[3, :3]
        if not np.allclose(actual - (centers[suffix] - shift), delta, atol=1e-5):
            raise ValueError("Wheel origins are inconsistent; refusing an ambiguous translation")
    previous_path = package / "road_contact_repair.json"
    previous_report = json.loads(previous_path.read_text()) if previous_path.exists() else None
    original_backup = Path(previous_report["original_backup"]) if previous_report and "original_backup" in previous_report else None
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = package / "backups" / ("before_road_contact_" + stamp)
    backup.mkdir(parents=True)
    shutil.copytree(data, backup / "data")
    shutil.copy2(model_path, backup / model_path.name)
    if (car / "collider.kn5").exists():
        shutil.copy2(car / "collider.kn5", backup / "collider.kn5")
    if original_backup is None:
        original_backup = backup
    for child in model.root.children:
        if child.kind != 1:
            raise ValueError("Expected grouped model root")
        matrix = child.matrix
        matrix[3, :3] -= delta
        child.payload = bytearray(matrix.astype("<f4").tobytes())
    model.write(model_path)
    radii = {}
    for suffix in ("LF", "LR"):
        points = np.concatenate(list(world_vertices(nodes["WHEEL_" + suffix])))
        radii[suffix] = round(float(np.linalg.norm(points[:, 1:3], axis=1).max()), 5)
    front_radius, rear_radius = radii["LF"], radii["LR"]
    cp = ini(data / "car.ini")
    set_values(cp, "BASIC", {"GRAPHICS_OFFSET": "0,0,0", "GRAPHICS_PITCH_ROTATION": 0,
                            "TOTALMASS": round(spec["mass"])})
    camera = spec["camera"]
    if camera:
        eye = np.array([-camera[0], camera[2], camera[1]]) - shift
        eye_text = ",".join(f"{v:.6f}" for v in eye)
        set_values(cp, "GRAPHICS", {"DRIVEREYES": eye_text, "BONNET_CAMERA_POS": eye_text,
                                   "ON_BOARD_PITCH_ANGLE": camera[6], "BONNET_CAMERA_PITCH": camera[6]})
        dash = ini(data / "dash_cam.ini")
        set_values(dash, "DASH_CAM", {"POS": eye_text, "PITCH_ANGLE": camera[6]})
        save(dash, data / "dash_cam.ini")
    save(cp, data / "car.ini")
    susp = ini(data / "suspensions.ini")
    wheelbase = centers["LF"][2] - centers["LR"][2]
    set_values(susp, "BASIC", {"WHEELBASE": wheelbase, "CG_LOCATION": 0.5})
    axles = spec["axles"]
    for section, suffix, axle_set, hubmass in (
            ("FRONT", "LF", axles[:1], 170 if family != "scania" else 120),
            ("REAR", "LR", axles[1:2] if family == "scania" else axles[1:],
             300 if family != "scania" else 220)):
        rate = sum(v["achse_feder"] for v in axle_set) * 1000
        damper = sum(v.get("achse_daempfer", 18) for v in axle_set) * 1000
        sprung_load = max(0, spec["mass"] * .25 - hubmass) * 9.81
        set_values(susp, section, {"BASEY": centers[suffix][1] - shift[1],
                   "TRACK": centers[suffix][0] - centers["RF" if suffix == "LF" else "RR"][0],
                   "ROD_LENGTH": round(sprung_load / rate, 6), "HUB_MASS": hubmass,
                   "SPRING_RATE": rate, "BUMP_STOP_RATE": 1000000,
                   "BUMPSTOP_UP": .18, "BUMPSTOP_DN": .16, "PACKER_RANGE": .25,
                   "DAMP_BUMP": damper, "DAMP_REBOUND": damper * 1.35,
                   "DAMP_FAST_BUMP": damper * .7, "DAMP_FAST_REBOUND": damper})
    for section in ("HEAVE_FRONT", "HEAVE_REAR"):
        susp.remove_section(section)
    save(susp, data / "suspensions.ini")
    tyres = ini(data / "tyres.ini")
    for section, radius in (("FRONT", front_radius), ("REAR", rear_radius)):
        set_values(tyres, section, {"RADIUS": radius, "FZ0": round(spec["mass"] * 9.81 / 4),
                                   "RADIUS_ANGULAR_K": .001})
    save(tyres, data / "tyres.ini")
    # The source torque curve already describes engine torque; avoid donor turbo multiplication.
    engine = ini(data / "engine.ini")
    for section in list(engine.sections()):
        if section.startswith("TURBO_"):
            engine.remove_section(section)
    curve = spec["curve"]
    idle = spec["engine_constants"].get("engine_governed_idle_RPM", 650 if family == "atenu" else 700)
    limiter = min(spec["engine_constants"].get("engine_maxrpm", curve[-1][0]), curve[-1][0])
    up = min(limiter - 150, max(rpm for rpm, torque in curve if torque > 0) - 100)
    set_values(engine, "ENGINE_DATA", {"LIMITER": limiter, "MINIMUM": idle})
    save(engine, data / "engine.ini")
    # Some donor schemas retain this unused filename even with FROM_COAST_REF.
    coast_path = data / engine["COAST_CURVE"]["FILENAME"]
    if not coast_path.exists():
        coast_path.write_text(f"0|0\n{engine['COAST_REF']['RPM']}|-{engine['COAST_REF']['TORQUE']}\n", encoding="utf-8")
    (data / "power.lut").write_text("".join(f"{rpm:g}|{torque:g}\n" for rpm, torque in curve), encoding="utf-8")
    gears = spec["gear_constants"]
    drive = ini(data / "drivetrain.ini")
    if family == "dragon":
        # DIWA first gear is hydraulic, not a fixed 1.36 reduction. AC has no
        # equivalent converter: retain the adapted mechanical first/reverse,
        # but use the two locked source ratios and source final drive.
        ratios = [float(drive["GEARS"]["GEAR_1"]), gears["antrieb_getr_ratio2"], gears["antrieb_getr_ratio3"]]
        reverse = float(drive["GEARS"]["GEAR_R"])
    else:
        ratios = [gears[f"antrieb_getr_ratio{i}"] for i in range(1, 7)]
        reverse = -abs(gears["antrieb_getr_ratioR"])
    set_values(drive, "GEARS", {"COUNT": len(ratios), "GEAR_R": reverse,
                               "FINAL": gears["antrieb_i_achse"],
                               **{f"GEAR_{i}": v for i, v in enumerate(ratios, 1)}})
    set_values(drive, "GEARBOX", {"SUPPORTS_SHIFTER": 0})
    set_values(drive, "CLUTCH", {"MAX_TORQUE": round(max(t for _, t in curve) * 1.5)})
    set_values(drive, "AUTOCLUTCH", {"FORCED_ON": 1, "MIN_RPM": idle + 100, "MAX_RPM": idle + 500})
    set_values(drive, "AUTO_SHIFTER", {"UP": up, "DOWN": 1000})
    save(drive, data / "drivetrain.ini")
    ai = ini(data / "ai.ini")
    set_values(ai, "GEARS", {"UP": up, "DOWN": 1000})
    save(ai, data / "ai.ini")
    curve_source = ac / "content/cars/kmb_e200_drivable/data/tcurve_bus.lut"
    for section in ("THERMAL_FRONT", "THERMAL_REAR"):
        curve_path = data / tyres[section]["PERFORMANCE_CURVE"]
        if not curve_path.exists():
            shutil.copy2(curve_source, curve_path)
    # Use a real convex hull as well as the AABB, with its base clear of the tires' ground plane.
    body = nodes["BODY"]
    points = np.concatenate(list(world_vertices(body)))
    lo, hi = points.min(0), points.max(0)
    width = spec["width"] - .04
    low = np.array([-width / 2, .30 - shift[1], lo[2] + .15])
    high = np.array([width / 2, hi[1] - .1, hi[2] - .15])
    collider = Kn5(ac / "content/cars/kmb_e200_drivable/collider.kn5")
    vertices = np.concatenate([n.vertices[:, :3] for _, n in collider.root.walk() if n.kind == 2])
    old_low, old_high = vertices.min(0), vertices.max(0)
    for _, node in collider.root.walk():
        if node.kind == 1:
            node.payload = bytearray(np.eye(4, dtype="<f4").tobytes())
        else:
            node.vertices[:, :3] = (node.vertices[:, :3] - old_low) / (old_high - old_low) * (high - low) + low
            bounds(node)
    collider.write(car / "collider.kn5")
    col = configparser.ConfigParser()
    col.optionxform = str
    set_values(col, "COLLIDER_0", {"CENTRE": ",".join(f"{v:.6f}" for v in (low + high) / 2),
                                  "SIZE": ",".join(f"{v:.6f}" for v in high - low), "GROUND_ENABLE": 1})
    save(col, data / "colliders.ini")
    for path in data.glob("*.ini"):
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.split(";", 1)[0].strip()
            if "=" in line:
                value = line.split("=", 1)[1].strip()
                if value.lower().endswith(".lut") and not (data / value).exists():
                    raise ValueError(f"Missing physics LUT: {path.name}: {value}")
    result = {"family": family, "car_id": car.name, "backup": str(backup),
              "original_backup": str(original_backup),
              "source_cg_height": spec["cg_height"], "model_translation": (-delta).tolist(),
              "origin_shift_from_omsi": shift.tolist(), "radii": radii,
              "engine_file": spec["engine_file"], "gearbox_file": spec["gearbox_file"],
              "shift_up_rpm": up, "limiter_rpm": limiter, "runtime_test": "pending user retest",
              "gear_count": len(ratios),
              "warnings": ["AC has two physical axles; third axle remains visual", "50/50 AC axle weight split is an adaptation"]}
    if family == "dragon":
        result["warnings"].append("DIWA hydraulic first/reverse approximated by existing AC mechanical ratios")
    for suffix in ("LF", "RF", "LR", "RR"):
        actual = nodes["HUB_" + suffix].matrix[3, :3]
        expected = centers[suffix] - shift
        if not np.allclose(actual, expected, atol=1e-5):
            raise ValueError(f"Pivot alignment failed: {suffix}")
    if install:
        processes = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"], capture_output=True, text=True, check=True)
        if '"acs.exe"' in processes.stdout.lower():
            raise RuntimeError("Close Assetto Corsa before installation")
        target = ac / "content/cars" / car.name
        installed_backup = backup / "installed"
        candidates = [p for p in [model_path, car / "collider.kn5", *data.glob("*")]
                      if p.is_file() and (not (target / p.relative_to(car)).exists()
                      or not (backup / p.relative_to(car)).exists()
                      or p.read_bytes() != (backup / p.relative_to(car)).read_bytes())]
        changed = [p for p in candidates if p.is_file() and (
            not (target / p.relative_to(car)).exists() or
            p.read_bytes() != (target / p.relative_to(car)).read_bytes())]
        # Check for newer edits before replacing any installed file.
        for path in changed:
            rel = path.relative_to(car)
            dest = target / rel
            baselines = [old / rel for old in (backup, original_backup)]
            if dest.exists() and not any(old.exists() and dest.read_bytes() == old.read_bytes() for old in baselines):
                raise ValueError(f"Installed file has independent changes: {dest}")
        hashes = dict(previous_report.get("installed_sha256", {})) if previous_report else {}
        for path in changed:
            if not path.is_file():
                continue
            rel = path.relative_to(car)
            dest = target / rel
            if dest.exists():
                old = installed_backup / rel
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, old)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != hashlib.sha256(dest.read_bytes()).hexdigest():
                raise ValueError(f"Install hash mismatch: {dest}")
            hashes[str(rel)] = digest
        result.update(installed=str(target), installed_sha256=hashes)
    report.update(omsi_engine_curve_used=curve, wheel_centers_frame="OMSI source",
                  ac_origin_shift=shift.tolist(), road_contact_report="road_contact_repair.json")
    if family == "dragon":
        report.update(wheel_centers={k: v.tolist() for k, v in centers.items()},
                      axle_mapping="rear driven; intermediate visual", wheel_layout="three-axle; intermediate axle visual")
    (package / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (package / "road_contact_repair.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    print(json.dumps(repair(args.package, install=args.install), indent=2))
