"""Build separate ground-centered KMB models for the installed CSP Traffic Planner.

Dependencies: numpy, scipy, Pillow, fast-simplification. All large outputs stay
outside Git. Close AC before --install. Original driveable cars are read-only.
"""
import argparse
import copy
import datetime
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess

import fast_simplification
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from kn5_tools import Kn5, Node, read_u32, read_string
from prepare_kmb_ai_grid import ROOT, buses, audit_bus, write_backed_up
from repair_omsi_bus_physics import AC, bounds, ini, world_vertices


def textures(model, skin, size):
    source = io.BytesIO(model.prefix)
    source.seek(6)
    if read_u32(source) > 5:
        read_u32(source)
    updates = {}
    for _ in range(read_u32(source)):
        read_u32(source)
        name = read_string(source)
        raw = source.read(read_u32(source))
        override = skin / name
        if Path(name).name == name and override.is_file():
            raw = override.read_bytes()
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            im.thumbnail((size, size), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            im.save(out, format="PNG")
            updates[name] = out.getvalue()
        except (OSError, ValueError):
            updates[name] = raw
    model.rebuild_prefix(updates)


def simplify(model):
    for _, n in model.root.walk():
        if n.kind != 2 or n.index_count < 180:
            continue
        # Keep small signs and transparent glass intact; simplify larger solids.
        mat = model.materials[n.material_id]
        if mat["blend"] or any(s in n.name.lower() for s in ("display", "hanover", "gorba", "sign")):
            continue
        vertices = n.vertices.copy()
        start = n.vertex_offset + n.vertex_count * n.vertex_stride
        faces = np.frombuffer(n.payload, dtype="<u2", count=n.index_count, offset=start + 4).reshape(-1, 3).copy()
        target = max(16, int(len(faces) * .08))
        points, triangles = fast_simplification.simplify(vertices[:, :3].astype(float), faces.astype(np.int32), target_count=target)
        if not len(points) or not len(triangles) or len(points) >= 65536:
            continue
        # Recover normal, UV and tangent attributes from the nearest source seam.
        nearest = cKDTree(vertices[:, :3]).query(points)[1]
        v = vertices[nearest]
        v[:, :3] = points
        tail = n.payload[start + 4 + n.index_count * 2:]
        n.payload = bytearray(n.payload[:n.vertex_offset - 4] + struct.pack("<I", len(v)) +
                              v.astype("<f4").tobytes() + struct.pack("<I", triangles.size) +
                              triangles.astype("<u2").tobytes() + tail)
        n.vertex_count, n.index_count = len(v), triangles.size
        bounds(n)


def move(node, offset):
    if node.kind == 1:
        matrix = node.matrix
        matrix[3, :3] += offset
        node.payload = bytearray(matrix.astype("<f4").tobytes())
    else:
        node.vertices[:, :3] += offset
        bounds(node)


def build(ac, bus, out):
    car = ac / "content/cars" / bus["id"]
    check = audit_bus(ac, bus)
    if check["errors"]:
        raise ValueError(check)
    model = Kn5(car / (car.name + ".kn5"))
    if not np.allclose(model.root.matrix, np.eye(4)):
        raise ValueError("Unexpected car root transformation")
    nodes = {n.name: n for _, n in model.root.walk()}
    points = np.concatenate(list(world_vertices(model.root)))
    low, high = points.min(0), points.max(0)
    center_z = (low[2] + high[2]) / 2
    offset = np.array([0, bus["cg_height"], -center_z])
    front_pos, rear_pos = [nodes["HUB_" + k].matrix[3, :3].copy() for k in ("LF", "LR")]
    body, wheels, extra = [], [], []
    for child in model.root.children:
        if child.name.startswith("HUB_"):
            suffix = child.name[4:]
            wh = nodes["WHEEL_" + suffix]
            matrix = wh.matrix @ child.matrix
            wh.payload = bytearray(matrix.astype("<f4").tobytes())
            move(wh, offset)
            wheels.append(wh)
        elif child.name in ("E6M_TAG_LR", "E6M_TAG_RR", "OMSI_TAG_TAG_L", "OMSI_TAG_TAG_R"):
            samples = np.concatenate(list(world_vertices(child)))
            pivot = child.matrix[3, :3]
            radius = float(np.linalg.norm(samples[:, 1:3] - pivot[1:3], axis=1).max())
            extra.append({"node": child.name, "radius": radius})
            move(child, offset)
            wheels.append(child)
        else:
            if child.name == "BODY":
                child.name = "OMSI_SOURCE_BODY"
            move(child, offset)
            body.append(child)
    model.root.children = [Node.dummy("BODY", body), *wheels]
    prefix = "hk_" + car.name
    out.mkdir(parents=True, exist_ok=True)
    textures(model, car / "skins" / bus["skin"], 1024)
    main_path = out / (prefix + ".kn5")
    model.write(main_path)
    main_triangles = sum(n.index_count // 3 for _, n in model.root.walk() if n.kind == 2)
    lod = copy.deepcopy(model)
    simplify(lod)
    textures(lod, Path("__no_skin_overrides__"), 256)
    lod_path = out / (prefix + "_lod.kn5")
    lod.write(lod_path)
    lod_triangles = sum(n.index_count // 3 for _, n in lod.root.walk() if n.kind == 2)
    collider = Kn5(car / "collider.kn5")
    for child in collider.root.children:
        move(child, offset)
    collider_path = out / (prefix + "_collider.kn5")
    collider.write(collider_path)
    mass = float(ini(car / "data/car.ini")["BASIC"]["TOTALMASS"])
    tyres = ini(car / "data/tyres.ini")
    definition = {
        "main": main_path.name, "lod": lod_path.name, "collider": collider_path.name,
        "color": "vintage", "maxSpeed": 70, "dynamic": .4, "chance": .25,
        "lights": {"headlights": [], "rear": [], "brakes": [], "rearCombined": []},
        "dimensions": {"front": float(high[2] - front_pos[2]), "rear": float(front_pos[2] - low[2]),
                       "turningOffset": float(front_pos[2] - rear_pos[2]), "width": float(high[0] - low[0]),
                       "wheelRadius": float(tyres["FRONT"]["RADIUS"]),
                       "fakeShadowX": float((high[0] - low[0]) / 2), "fakeShadowZ": float((high[2] - low[2]) / 2)},
        "physics": {"mass": mass, "width": float(front_pos[0] - nodes["HUB_RF"].matrix[3, 0]),
                    "length": float(front_pos[2] - rear_pos[2]), "wheelsGripForce": 12,
                    "suspensionTravel": .12, "suspensionForce": 48, "suspensionDamping": 20,
                    "cog": [0, bus["cg_height"], float(-center_z)]},
        "kmbExtraWheels": extra,
    }
    # Validate saved geometry and dimensions, not just the in-memory editor.
    saved = Kn5(main_path)
    if sum(n.name == "BODY" for _, n in saved.root.walk()) != 1:
        raise ValueError("Traffic model must have exactly one body motion node")
    all_points = np.concatenate(list(world_vertices(saved.root)))
    if abs(all_points[:, 2].min() + all_points[:, 2].max()) > .001:
        raise ValueError("Traffic model is not centered between bumpers")
    for suffix in ("LF", "RF", "LR", "RR"):
        wheel = next(n for n in saved.root.children if n.name == "WHEEL_" + suffix)
        relative = np.concatenate(list(world_vertices(wheel)))[:, 1].min()
        if abs(relative) > .04:
            raise ValueError(f"Traffic wheel ground mismatch: {car.name}/{suffix}: {relative}")
    hull = np.concatenate(list(world_vertices(Kn5(collider_path).root)))
    if hull[:, 1].min() < .1:
        raise ValueError("Traffic collider below intended ground clearance")
    if lod_triangles >= main_triangles:
        raise ValueError("LOD reduction failed")
    json_path = out / (prefix + ".json")
    json_path.write_text(json.dumps(definition, indent=2), encoding="utf-8")
    return {"car": car.name, "main_triangles": main_triangles, "lod_triangles": lod_triangles,
            "extra_axle_nodes": extra, "translation_from_ac": offset.tolist(),
            "main_mb": round(main_path.stat().st_size / 1e6, 2), "lod_mb": round(lod_path.stat().st_size / 1e6, 2),
            "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                      (main_path, lod_path, collider_path, json_path)}, "status": "PASS"}


def patch_extra_axles(tool, backup):
    path = tool / "src/simulation/TrafficCarFullLOD.lua"
    source = path.read_text(encoding="utf-8")
    marker = "-- KMB_EXTRA_AXLES_V1"
    if marker in source:
        return
    anchor = "  self._wheels = wheels"
    if source.count(anchor) != 1:
        raise ValueError("Unknown TrafficCarFullLOD version; no Lua changes installed")
    source = source.replace(anchor, anchor + "\n" + marker + "\n" +
        "  self._kmbExtraWheels = {}\n"
        "  for _, item in ipairs(car.definition.kmbExtraWheels or {}) do\n"
        "    self._kmbExtraWheels[#self._kmbExtraWheels + 1] = {\n"
        "      node = modelMain:findNodes(item.node), radius = item.radius\n"
        "    }\n  end")
    anchor = "  -- ac.perfFrameBegin(1093)"
    if source.count(anchor) != 1:
        raise ValueError("Unknown traffic update method")
    source = source.replace(anchor,
        "  if not car:crashed() then\n"
        "    for _, item in ipairs(self._kmbExtraWheels or {}) do\n"
        "      item.node:setRotation(_dirSide, self._drivenDistance / item.radius)\n"
        "    end\n  end\n\n" + anchor)
    write_backed_up(path, source.encode("utf-8"), backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/KMB_AI")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.install:
        procs = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"], capture_output=True, text=True, check=True)
        if '"acs.exe"' in procs.stdout.lower():
            raise RuntimeError("Close Assetto Corsa before installing traffic assets")
    out = args.output / "planner_data"
    results = []
    for bus in buses():
        result = build(args.ac, bus, out)
        results.append(result)
        print(json.dumps({k: result[k] for k in ("car", "status", "main_triangles", "lod_triangles", "main_mb", "lod_mb")}), flush=True)
    if args.install:
        tool = args.ac / "extension/lua/tools/csp-traffic-tool"
        backup = args.output / "backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        patch_extra_axles(tool, backup)
        for result in results:
            for name, digest in result["files"].items():
                dest = tool / "data" / name
                write_backed_up(dest, (out / name).read_bytes(), backup / "planner_data")
                if hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
                    raise ValueError("Installed traffic hash mismatch: " + name)
    report = {"status": "PASS", "buses": results, "installed": args.install,
              "runtime_test": "pending user Traffic Planner test",
              "limitations": ["No OMSI passenger service", "Traffic lights are not bound to source lamp meshes",
                              "CSP Traffic Planner definitions; other traffic systems use their own vehicle lists"]}
    (args.output / "planner_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
