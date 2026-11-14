"""Read back installed KMB Traffic Planner models/definitions and build hashes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from kn5_tools import Kn5
from prepare_kmb_ai_grid import ROOT, buses
from repair_omsi_bus_physics import AC, world_vertices


def audit(ac, output):
    report = json.loads((output / "planner_validation.json").read_text(encoding="utf-8"))
    installed = ac / "extension/lua/tools/csp-traffic-tool"
    checks = []
    for bus, built in zip(buses(), report["buses"], strict=True):
        prefix = "hk_" + bus["id"]
        definition = json.loads((installed / "data" / (prefix + ".json")).read_text(encoding="utf-8"))
        errors, vertices, lod_tris = [], [], []
        for name, digest in built["files"].items():
            path = installed / "data" / name
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                errors.append("Installed hash mismatch: " + name)
        for key in ("main", "lod", "collider"):
            model = Kn5(installed / "data" / definition[key])
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
        for axis in range(3):
            if max(abs(vertices[1][:, axis].min() - low[axis]), abs(vertices[1][:, axis].max() - high[axis])) > .15:
                errors.append("Distant LOD changed overall silhouette bounds")
        checks.append({"car": bus["id"], "status": "PASS" if not errors else "FAIL", "errors": sorted(set(errors))})
    source = (installed / "src/simulation/TrafficCarFullLOD.lua").read_text(encoding="utf-8")
    from luaparser import ast
    ast.parse(source)
    if "-- KMB_EXTRA_AXLES_V1" not in source:
        raise ValueError("Extra-axle support is not installed")
    result = {"status": "PASS" if all(not c["errors"] for c in checks) else "FAIL", "buses": checks,
              "lua_syntax": "PASS", "runtime": "pending user Traffic Planner test"}
    (output / "planner_installed_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/KMB_AI")
    args = parser.parse_args()
    result = audit(args.ac, args.output)
    print(json.dumps(result, indent=2))
    raise SystemExit(result["status"] != "PASS")
