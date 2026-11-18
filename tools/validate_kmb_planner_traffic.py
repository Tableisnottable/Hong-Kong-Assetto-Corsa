"""Read back installed KMB Traffic Planner models/definitions and build hashes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from kn5_tools import Kn5
from prepare_kmb_ai_grid import ROOT, buses
from repair_omsi_bus_physics import AC, world_vertices
from build_kmb_bus_lods import validate_lod, triangle_count, TRAFFIC_BANDS


def audit(ac, output, staged=False):
    report = json.loads((output / "planner_validation.json").read_text(encoding="utf-8"))
    installed = ac / "extension/lua/tools/csp-traffic-tool"
    models = output / 'planner_data' if staged else installed / 'data'
    checks = []
    for bus, built in zip(buses(), report["buses"], strict=True):
        prefix = "hk_" + bus["id"]
        definition = json.loads((models / (prefix + ".json")).read_text(encoding="utf-8"))
        errors, vertices, lod_tris = [], [], []
        for name, digest in built["files"].items():
            path = models / name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append("Installed hash mismatch: " + name)
        for key in ("main", "lod", "collider"):
            model = Kn5(models / definition[key])
            points = np.concatenate(list(world_vertices(model.root)))
            vertices.append(points)
            if key != "collider":
                roots = {n.name for n in model.root.children}
                if not {"BODY", "WHEEL_LF", "WHEEL_RF", "WHEEL_LR", "WHEEL_RR"} <= roots:
                    errors.append(key + " wheel/body nodes are not top-level")
                if sum(n.name == "BODY" for _, n in model.root.walk()) != 1:
                    errors.append(key + " has ambiguous body motion nodes")
                for extra in definition["kmbExtraWheels"]:
                    if extra["node"] not in roots or not .3 < extra["radius"] < .7:
                        errors.append(key + " invalid extra wheel binding")
                textures = {t["name"] for t in model.textures}
                for mat in model.materials:
                    for tex in mat["maps"]:
                        if tex["texture"] not in textures:
                            errors.append(key + " missing embedded texture " + tex["texture"])
                lod_tris.append(sum(n.index_count // 3 for _, n in model.root.walk() if n.kind == 2))
                if key == "main":
                    points = definition["physics"].get("wheelBasePoints", [])
                    if len(points) != 4:
                        errors.append("Missing four measured traffic suspension points")
                    else:
                        for suffix, point in zip(("LF", "RF", "LR", "RR"), points, strict=True):
                            pivot = next(n for n in model.root.children if n.name == "WHEEL_" + suffix).matrix[3, :3]
                            if max(abs(float(pivot[0]) - point[0]), abs(float(pivot[2]) - point[2])) > .002 or abs(point[1] - 1) > .001:
                                errors.append(key + " suspension point misses rendered axle " + suffix)
        low, high = vertices[0].min(0), vertices[0].max(0)
        dims = definition["dimensions"]
        if abs(dims["front"] + dims["rear"] - (high[2] - low[2])) > .002:
            errors.append("Traffic spacing disagrees with body length")
        if abs(low[2] + high[2]) > .002:
            errors.append("Body is not centered")
        if vertices[2][:, 1].min() < .1:
            errors.append("Collider too close to road")
        if lod_tris[1] >= lod_tris[0]:
            errors.append("No distant geometry reduction")
        levels = definition.get('kmbLods', [])
        if len(levels) != 4 or [v['distance'] for v in levels] != list(TRAFFIC_BANDS):
            errors.append('Missing or unordered traffic LOD 1-4 distances')
        else:
            if levels[0]['file'] != definition['lod']:
                errors.append('Planner fallback must use LOD 1')
            reference = Kn5(models / definition['main'])
            previous = triangle_count(reference)
            for item in levels:
                try:
                    previous = validate_lod(models / item['file'], reference, previous)
                except (ValueError, OSError) as exc:
                    errors.append(str(exc))
        for axis in range(3):
            if max(abs(vertices[1][:, axis].min() - low[axis]), abs(vertices[1][:, axis].max() - high[axis])) > .15:
                errors.append("Distant LOD changed overall silhouette bounds")
        checks.append({"car": bus["id"], "status": "PASS" if not errors else "FAIL", "errors": sorted(set(errors))})
    source = (installed / "src/simulation/TrafficCarFullLOD.lua").read_text(encoding="utf-8")
    from luaparser import ast
    ast.parse(source)
    if "-- KMB_EXTRA_AXLES_V1" not in source:
        raise ValueError("Extra-axle support is not installed")
    physics_source = (installed / "src/simulation/TrafficCarPhysics.lua").read_text(encoding="utf-8")
    ast.parse(physics_source)
    if "-- KMB_WHEEL_BASE_POINTS_V1" not in physics_source:
        raise ValueError("Measured wheel-contact support is not installed")
    lod_module = ROOT / 'tools/kmb_traffic_lods.lua' if staged else installed / 'src/simulation/KmbBusLODs.lua'
    lod_source = lod_module.read_text(encoding='utf-8')
    ast.parse(lod_source)
    car_source = (installed / 'src/simulation/TrafficCar.lua').read_text(encoding='utf-8')
    ast.parse(car_source)
    if not staged and ('-- KMB_DISTANCE_LODS_V1' not in car_source or 'KmbBusLODs.update(self)' not in car_source):
        raise ValueError('Traffic LOD 2-4 switching is not installed')
    result = {"status": "PASS" if all(not c["errors"] for c in checks) else "FAIL", "buses": checks,
              "scope": "staged models" if staged else "installed models",
              "lua_syntax": "PASS", "runtime": "pending user Traffic Planner test"}
    name = 'planner_staged_validation.json' if staged else 'planner_installed_validation.json'
    (output / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/KMB_AI")
    parser.add_argument("--staged", action="store_true", help="Check staged models without requiring Planner changes to be installed")
    args = parser.parse_args()
    result = audit(args.ac, args.output, args.staged)
    print(json.dumps(result, indent=2))
    raise SystemExit(result["status"] != "PASS")
