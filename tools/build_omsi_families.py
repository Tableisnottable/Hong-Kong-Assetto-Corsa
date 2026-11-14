"""Build local AC KN5 cars from the four remaining KMB OMSI O3D families."""
from __future__ import annotations

import argparse
import configparser
import hashlib
import importlib.util
import io
import json
import math
import re
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OMSI = Path(r"A:/SteamLibrary/steamapps/common/OMSI 2/Vehicles")
AC = Path(r"A:/SteamLibrary/steamapps/common/assettocorsa")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kn5_tools import Kn5, Node, string_bytes

spec = importlib.util.spec_from_file_location(
    "o3dreader", Path(__file__).resolve().parent / "vendor/o3dconvert.py"
)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

FAMILIES = {
    "atenu": {
        "source": "ADL_E500MMC_KMB_ATENU", "cfg": "Model/model_ATENU.cfg",
        "bus": "ATENU.bus", "engine_const": "Script/engine_constfile_D92_ZF_D28_turbo.txt",
        "id": "kmb_atenu_drivable", "name": "KMB ADL E500MMC ATENU",
        "donor": "bk_bus_neoplan_cent",
        "wheel_pattern": re.compile(r"(?:^|[\\/])whl([0-5])(?:_o)?\.o3d$", re.I),
        "third_axle": True,
    },
    "atee": {
        "source": "ADL_Enviro500_KMB_ATEE_WV820", "cfg": "Model/model_ATEE_exLWB.cfg",
        "bus": "ATEE_Ex_LWB.bus", "engine_const": "Script/engine_constfile_ISL8.9e5340B.txt",
        "id": "kmb_atee_drivable", "name": "KMB ADL Enviro500 ATEE",
        "donor": "bk_bus_neoplan_cent",
        "wheel_pattern": re.compile(r"(?:^|[\\/])wh([0-5])\.o3d$", re.I),
        "third_axle": True,
    },
    "dragon": {
        "source": "Dennis_Dragon 9.9M_KMB_ADS186_235", "cfg": "Model/model_ADS146.cfg",
        "bus": "Dennis_Dragon_ADS186-235_NPHxMB.bus", "engine_const": "Script_MB/engine_constfile_M250E20.txt",
        "id": "kmb_dennis_dragon_9m_drivable", "name": "KMB Dennis Dragon 9.9M",
        "donor": "bk_bus_dennis_dragon_9m",
        "wheel_pattern": re.compile(r"(?:^|[\\/])wh([0-5])\.o3d$", re.I),
        "third_axle": True,
    },
    "scania": {
        "source": "Scania_K230UB_KMB_ASB_ASC_4479", "cfg": "Model/model_ASB_Gorba.cfg",
        "bus": "ASB_Gorba.bus", "engine_const": "Script_MB/engine_constfile_D9A300.txt",
        "id": "kmb_scania_k230ub_drivable", "name": "KMB Scania K230UB",
        "donor": "kmb_e200_drivable",
        "wheel_pattern": re.compile(r"ASB[\\/]whl([0-3])(?:1)?\.o3d$", re.I),
        "third_axle": False,
    },
}


def cfg_blocks(text: str) -> list[dict]:
    blocks = []
    current = None
    command = None
    for line_no, line in enumerate(text.splitlines(), 1):
        m = re.fullmatch(r"\[([^]]+)\]", line.strip())
        if m:
            tag = m.group(1).strip().lower()
            command = {"tag": tag, "args": [], "line": line_no}
            if tag == "mesh":
                current = {"path": "", "commands": []}
                blocks.append(current)
            elif current is not None:
                current["commands"].append(command)
            continue
        if command is not None:
            command["args"].append(line.strip())
            if command["tag"] == "mesh" and current is not None and not current["path"]:
                current["path"] = line.strip()
    return [b for b in blocks if b["path"]]


def omsi_spec(source: Path, specdata: dict) -> tuple[float, list[tuple[int, int]]]:
    bus_path = source / specdata["bus"]
    bus_text = bus_path.read_text(encoding="cp1252", errors="replace")
    mass_match = re.search(r"(?m)^\[mass\]\s*\r?\n\s*([0-9]+(?:\.[0-9]+)?)", bus_text)
    if not mass_match:
        raise ValueError(f"Could not read OMSI mass from {bus_path}")
    const_path = source / specdata["engine_const"]
    const_text = const_path.read_text(encoding="cp1252", errors="replace")
    curve_match = re.search(r"(?ms)^\[newcurve\]\s*\r?\nengine_M_maxThrottle\s*(.*?)(?=^\[newcurve\]|\Z)", const_text)
    if not curve_match:
        raise ValueError(f"Could not read OMSI engine torque curve from {const_path}")
    points = [(int(float(rpm)), int(float(torque))) for rpm, torque in re.findall(
        r"(?ms)^\[pnt\]\s*\r?\n\s*([0-9.]+)\s*\r?\n\s*([0-9.]+)", curve_match.group(1)
    )]
    if len(points) < 4:
        raise ValueError(f"OMSI engine torque curve is incomplete in {const_path}")
    return float(mass_match.group(1)) * 1000, points


def make_helpers(source: Path):
    texture_files = {}
    for path in (source / "Texture").rglob("*"):
        if path.is_file():
            texture_files.setdefault(path.name.casefold(), []).append(path)
    textures, materials, tex_cache, mat_cache = {}, [], {}, {}
    missing, dynamic, mirror_nodes = set(), set(), []

    def add_texture(name, rgba, glass=False):
        original = (name or "").replace("\\", "/")
        key = (original.casefold(), tuple(float(x) for x in rgba), glass)
        if key in tex_cache:
            return tex_cache[key]
        base = Path(original).name
        is_dynamic = bool(re.match(r"(?i)^(reflexion|texttexture)", base))
        candidates = [source / "Texture" / original, source / "Model" / original]
        candidates.extend(texture_files.get(base.casefold(), []))
        image_path = next((p for p in candidates if p.is_file()), None)
        if image_path:
            try:
                image = Image.open(image_path).convert("RGBA")
            except Exception:
                image_path = None
        if not image_path:
            if original and not is_dynamic:
                missing.add(original)
            if is_dynamic:
                dynamic.add(original)
            color = (30, 35, 38, 255) if is_dynamic else tuple(round(max(0, min(1, v)) * 255) for v in rgba)
            image = Image.new("RGBA", (8, 8), color)
        if max(image.size) > 2048:
            image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
        if glass:
            pixels = np.asarray(image).copy()
            alpha = pixels[:, :, 3]
            alpha[alpha < 250] = (alpha[alpha < 250].astype(float) * 0.28).astype(np.uint8)
            image = Image.fromarray(pixels)
        if rgba[3] < 0.999:
            alpha = (np.asarray(image.getchannel("A"), dtype=float) * max(0, rgba[3])).astype(np.uint8)
            image.putalpha(Image.fromarray(alpha))
        token = hashlib.sha1(repr(key).encode()).hexdigest()[:10]
        tex_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", Path(base or "plain").stem) + "_" + token + ".dds"
        stream = io.BytesIO()
        image.save(stream, format="DDS", pixel_format="DXT5")
        textures[tex_name] = stream.getvalue()
        tex_cache[key] = tex_name
        return tex_name

    def add_material(raw, option, glass):
        alpha = option.get("matl_alpha", ["0"])[0]
        if glass and alpha == "0":
            alpha = "2"
        rgba = tuple(raw[0])
        key = ((raw[4] or "").casefold(), rgba, alpha, glass)
        if key in mat_cache:
            return mat_cache[key]
        tex = add_texture(raw[4], rgba, glass)
        blend = int(alpha == "2" or rgba[3] < 0.999)
        alpha_test = int(alpha == "1")
        mat_name = f"{source.name[:12]}_M{len(materials)}_{Path(raw[4] or 'plain').stem}"
        props = {k: (float(v), 0., 0., 0., 0., 0., 0., 0., 0., 0.) for k, v in {
            "ksAmbient": .42, "ksDiffuse": .65, "ksSpecular": .3 if glass else .1,
            "ksSpecularEXP": 80 if glass else 25, "ksAlphaRef": .5,
        }.items()}
        materials.append({"name": mat_name, "shader": "ksPerPixelAlpha" if blend or alpha_test else "ksPerPixel",
                          "blend": blend, "alpha_test": alpha_test, "depth": int(bool(blend)), "props": props,
                          "maps": [{"name": "txDiffuse", "slot": 0, "texture": tex}]})
        index = len(materials) - 1
        mat_cache[key] = index
        return index

    return textures, materials, add_texture, add_material, missing, dynamic, mirror_nodes


def mesh_node(name, vertices, normals, uvs, faces, material, materials):
    idx, inverse = np.unique(faces, return_inverse=True)
    vertices, normals, uvs = vertices[idx].copy(), normals[idx].copy(), uvs[idx].copy()
    indices = inverse.reshape(-1, 3).astype("<u2")
    if len(idx) > 65535:
        raise ValueError(f"Mesh has too many unique vertices: {name}")
    edge_a = vertices[indices[:, 1]] - vertices[indices[:, 0]]
    edge_b = vertices[indices[:, 2]] - vertices[indices[:, 0]]
    uv_a = uvs[indices[:, 1]] - uvs[indices[:, 0]]
    uv_b = uvs[indices[:, 2]] - uvs[indices[:, 0]]
    det = uv_a[:, 0] * uv_b[:, 1] - uv_a[:, 1] * uv_b[:, 0]
    inv = np.divide(1., det, out=np.zeros_like(det), where=np.abs(det) > 1e-10)
    face_t = (edge_a * uv_b[:, 1, None] - edge_b * uv_a[:, 1, None]) * inv[:, None]
    tangents = np.zeros_like(vertices)
    for corner in range(3):
        np.add.at(tangents, indices[:, corner], face_t)
    tangents -= normals * np.sum(tangents * normals, axis=1)[:, None]
    length = np.linalg.norm(tangents, axis=1)
    tangents[length < 1e-10] = (1, 0, 0)
    tangents /= np.maximum(np.linalg.norm(tangents, axis=1)[:, None], 1e-10)
    packed = np.empty((len(idx), 11), dtype="<f4")
    packed[:, :3], packed[:, 3:6], packed[:, 6:8], packed[:, 8:11] = vertices, normals, uvs, tangents
    center = (vertices.min(0) + vertices.max(0)) / 2
    radius = float(np.linalg.norm(vertices - center, axis=1).max())
    transparent = bool(materials[material]["blend"])
    payload = bytearray(struct.pack("<???I", not transparent, True, transparent, len(idx)))
    payload += packed.tobytes() + struct.pack("<I", indices.size) + indices.tobytes()
    payload += struct.pack("<II2f4f?", material, 0, 0., 2000., *center, radius, True)
    return Node(2, name, True, payload, [], len(idx), 7, 44, indices.size, material)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("family", choices=FAMILIES)
    args = parser.parse_args()
    specdata = FAMILIES[args.family]
    source = OMSI / specdata["source"]
    mass_kg, power = omsi_spec(source, specdata)
    cfg = source / specdata["cfg"]
    if not cfg.is_file():
        raise FileNotFoundError(cfg)
    package = ROOT / "outputs" / (args.family.upper() + "_playable")
    car = package / "content/cars" / specdata["id"]
    car.mkdir(parents=True, exist_ok=True)
    donor = AC / "content/cars" / specdata["donor"]
    if not donor.is_dir():
        raise FileNotFoundError(donor)
    meshes = cfg_blocks(cfg.read_text(encoding="utf-8-sig", errors="replace"))
    textures, materials, add_texture, add_material, missing, dynamic, mirror_nodes = make_helpers(source)
    node_root = Node.dummy(specdata["id"])
    wheel_meshes = {i: [] for i in range(6)}
    body_nodes, seen = [], set()
    state = {"cp_lenkrad_visible": 1, "foglight": 0, "dashupmon_mode": 0}
    report_meshes, total_triangles = [], 0
    x_mirror = np.diag([-1., 1., 1.])

    for block in meshes:
        name = block["path"]
        lower = name.casefold()
        wheel_match = specdata["wheel_pattern"].search(name)
        if lower in seen or Path(name).name.casefold() == "shadow.o3d":
            continue
        if any(c["tag"] == "visible" and len(c["args"]) > 1 and state.get(c["args"][0], 0) != float(c["args"][1]) for c in block["commands"]):
            continue
        seen.add(lower)
        o3d = cfg.parent / name.replace("\\", "/")
        parsed = reader.import_o3d(o3d.read_bytes())
        verts = np.asarray([v[0] for v in parsed[1]], dtype=float)
        normals = np.asarray([v[1] for v in parsed[1]], dtype=float)
        uvs = np.asarray([v[2] for v in parsed[1]], dtype=float)
        verts = verts @ x_mirror
        normals = normals @ x_mirror
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-10)
        faces = np.asarray([t[0][::-1] for t in parsed[2]], dtype=np.int64)
        face_mats = np.asarray([t[1] for t in parsed[2]], dtype=np.int64)
        opts = {}
        slots, counter = {}, Counter()
        for index, mat in enumerate(parsed[3]):
            key = (mat[4] or "").casefold()
            slots[(key, counter[key])] = index
            counter[key] += 1
        active = None
        for command in block["commands"]:
            if command["tag"] in ("matl", "matl_change") and len(command["args"]) > 1:
                try:
                    active = slots.get((command["args"][0].casefold(), int(command["args"][1])))
                except ValueError:
                    active = None
            elif active is not None and command["tag"] in ("matl_alpha", "alphascale", "matl_nozwrite", "matl_noztest", "matl_transmap"):
                opts.setdefault(active, {})[command["tag"]] = command["args"][:2]
        wheel_index = int(wheel_match.group(1)) if wheel_match else None
        stem = re.sub(r"[^a-zA-Z0-9_]", "_", Path(name).stem)
        for mat_index, raw in enumerate(parsed[3]):
            part = faces[face_mats == mat_index]
            if not len(part):
                continue
            option = opts.get(mat_index, {})
            if any(x in option.get("alphascale", [""])[0].casefold() for x in ("rain", "wetness", "dirt")):
                continue
            glass = any(tag in stem.casefold() for tag in ("glass", "cpwin", "window")) and not re.search(r"(?i)(reflexion|reg\.bmp)", raw[4] or "")
            material = add_material(raw, option, glass)
            node = mesh_node(f"{specdata['id']}_{stem}_m{mat_index}", verts, normals, uvs, part, material, materials)
            if wheel_index is not None:
                wheel_meshes[wheel_index].append(node)
            else:
                body_nodes.append(node)
                if re.match(r"(?i)reflexion\d", raw[4] or ""):
                    mirror_nodes.append(node.name)
            total_triangles += len(part)
        report_meshes.append({"source": name, "triangles": len(parsed[2]), "wheel_index": wheel_index})

    if any(not wheel_meshes[i] for i in range(4)):
        raise RuntimeError(f"Missing one or more physical wheel meshes: {[i for i in range(4) if not wheel_meshes[i]]}")
    shift_z = 0.0
    wheel_centers = {}
    for index, pieces in wheel_meshes.items():
        if not pieces:
            continue
        points = np.concatenate([n.vertices[:, :3] for n in pieces])
        center = (points.min(0) + points.max(0)) / 2
        for n in pieces:
            n.vertices[:, :3] -= center
            offset = n.vertex_offset + n.vertex_count * n.vertex_stride + 4 + n.index_count * 2 + 4 + 4 + 8
            v = n.vertices[:, :3]
            c = (v.min(0) + v.max(0)) / 2
            struct.pack_into("<4f", n.payload, offset, *c, float(np.linalg.norm(v - c, axis=1).max()))
        suffix = ("LF", "RF", "LR", "RR", "TAG_L", "TAG_R")[index]
        if index < 4:
            node_root.children.append(Node.dummy("HUB_" + suffix, [Node.dummy("SUSP_" + suffix), Node.dummy("WHEEL_" + suffix, pieces)], center))
            wheel_centers[suffix] = center.tolist()
        else:
            node_root.children.append(Node.dummy("OMSI_TAG_" + suffix, pieces, center))
            wheel_centers[suffix] = center.tolist()
    node_root.children.append(Node.dummy("BODY", body_nodes))

    track = abs(wheel_centers["LF"][0] - wheel_centers["RF"][0])
    wheelbase = wheel_centers["LF"][2] - wheel_centers["LR"][2]

    # Build native KN5 material/texture tables around the converted OMSI meshes.
    prefix = io.BytesIO()
    prefix.write(b"sc6969" + struct.pack("<II", 5, len(textures)))
    for name, payload in textures.items():
        prefix.write(struct.pack("<I", 1) + string_bytes(name) + struct.pack("<I", len(payload)) + payload)
    prefix.write(struct.pack("<I", len(materials)))
    for mat in materials:
        prefix.write(string_bytes(mat["name"]) + string_bytes(mat["shader"]))
        prefix.write(struct.pack("<BBI", mat["blend"], mat["alpha_test"], mat["depth"]))
        prefix.write(struct.pack("<I", len(mat["props"])))
        for key, values in mat["props"].items():
            prefix.write(string_bytes(key) + struct.pack("<10f", *values))
        prefix.write(struct.pack("<I", len(mat["maps"])))
        for mapping in mat["maps"]:
            prefix.write(string_bytes(mapping["name"]) + struct.pack("<I", mapping["slot"]) + string_bytes(mapping["texture"]))
    model_path = car / (specdata["id"] + ".kn5")
    with model_path.open("wb") as f:
        f.write(prefix.getvalue())
        node_root.write(f)
    check = Kn5(model_path)
    assert sum(n.index_count for _, n in check.root.walk()) == sum(n.index_count for _, n in node_root.walk())

    shutil.copytree(donor, car, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.kn5", "skins", "ui", "*.png", "*.jpg", "*.jpeg"))
    # Re-write after donor copy in case the donor contains a same-named KN5.
    with model_path.open("wb") as f:
        f.write(prefix.getvalue())
        node_root.write(f)
    data_dir = car / "data"
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(data_dir / "car.ini", encoding="utf-8-sig")
    cp["INFO"]["SCREEN_NAME"] = specdata["name"]
    cp["BASIC"]["TOTALMASS"] = str(round(mass_kg))
    cp["GRAPHICS"]["DRIVEREYES"] = "-0.72,0.80,3.45"
    cp["GRAPHICS"]["USE_ANIMATED_SUSPENSIONS"] = "0"
    with (data_dir / "car.ini").open("w", encoding="utf-8") as f:
        cp.write(f, space_around_delimiters=False)
    lod = data_dir / "lods.ini"
    lod.write_text(f"[COCKPIT_HR]\nDISTANCE_SWITCH=0\n[LOD_0]\nFILE={specdata['id']}.kn5\nIN=0\nOUT=2000\n", encoding="utf-8")
    (data_dir / "power.lut").write_text("\n".join(f"{rpm}|{torque}" for rpm, torque in power) + "\n", encoding="utf-8")
    susp = configparser.ConfigParser(interpolation=None, strict=False)
    susp.optionxform = str
    susp.read(data_dir / "suspensions.ini", encoding="utf-8-sig")
    susp["BASIC"]["WHEELBASE"] = f"{wheelbase:.4f}"
    susp["FRONT"]["TRACK"] = f"{track:.4f}"
    susp["REAR"]["TRACK"] = f"{track:.4f}"
    with (data_dir / "suspensions.ini").open("w", encoding="utf-8") as f:
        susp.write(f, space_around_delimiters=False)
    for anim in car.glob("*.ksanim"):
        pass
    # Preserve source OMSI art under a local skin folder; no source files are modified.
    skin_dir = car / "skins" / "0_kmb"
    skin_dir.mkdir(parents=True, exist_ok=True)
    skin = {"skinname": f"KMB {args.family.upper()} OMSI source", "drivername": "", "country": "Hong Kong", "number": ""}
    (skin_dir / "ui_skin.json").write_text(json.dumps(skin, indent=2), encoding="utf-8")
    (skin_dir / "skin.ini").write_text("[driver]\nSUIT=black\nGLOVES=black\nHELMET=black\n", encoding="utf-8")
    if specdata["third_axle"]:
        ext_dir = car / "extension"
        ext_dir.mkdir(exist_ok=True)
        left, right = "OMSI_TAG_TAG_L", "OMSI_TAG_TAG_R"
        (ext_dir / "ext_config.ini").write_text(
            "[SCRIPT_...]\nSCRIPT=\"\nlocal car = ac.getCar()\n"
            "local root = car and ac.findNodes('carRoot:' .. car.index)\n"
            f"local left = root and root:findNodes('{left}')\n"
            f"local right = root and root:findNodes('{right}')\n"
            "local angle = 0\nfunction update(dt)\n"
            "  if not car then return end\n"
            "  angle = (angle + car.speedKmh / 3.6 / 0.5 * dt) % (2 * math.pi)\n"
            "  if left then left:setRotation(vec3(1, 0, 0), angle) end\n"
            "  if right then right:setRotation(vec3(1, 0, 0), angle) end\n"
            "end\n\"\n", encoding="utf-8"
        )
    ui_dir = car / "ui"
    ui_dir.mkdir(exist_ok=True)
    (ui_dir / "ui_car.json").write_text(json.dumps({
        "name": specdata["name"], "brand": "KMB", "country": "Hong Kong", "class": "street",
        "description": "Local Assetto Corsa conversion from the installed OMSI model. Basic AC driving physics; OMSI scripted systems are not ported.",
        "tags": ["bus", "KMB", args.family.upper()],
        "specs": {"weight": f"{round(mass_kg)} kg", "topspeed": "Bus gearing", "acceleration": "AC bus physics"}
    }, indent=2), encoding="utf-8")
    report = {
        "status": "built; awaiting validation and install", "family": args.family, "car_id": specdata["id"],
        "source": str(source), "source_cfg": str(cfg), "source_files_unchanged": True,
        "mesh_instances": len(report_meshes), "mesh_nodes": sum(1 for _, n in check.root.walk() if n.kind == 2),
        "triangles": total_triangles, "textures": len(textures), "materials": len(materials),
        "wheel_centers": wheel_centers, "wheel_layout": "three-axle; last axle visual" if specdata["third_axle"] else "two axle",
        "missing_textures": sorted(missing), "dynamic_textures": sorted(dynamic), "mesh_report": report_meshes,
        "omsi_engine_curve_used": power, "physics_mass_kg": round(mass_kg),
        "donor_physics": specdata["donor"], "warnings": ["Suspension, gearbox and sound base are adapted from the named AC donor", "OMSI scripts and clickable controls are not executed in AC"],
    }
    package.mkdir(parents=True, exist_ok=True)
    (package / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.family in ("atenu", "atee", "scania"):
        from repair_omsi_bus_physics import repair
        repair(package)
    print(json.dumps({k: report[k] for k in ("family", "mesh_instances", "mesh_nodes", "triangles", "textures", "wheel_centers", "missing_textures")}, indent=2))


if __name__ == "__main__":
    main()
