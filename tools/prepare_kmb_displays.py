"""Restore destination panels and generate route skins for all six KMB buses.

Reads installed OMSI artwork/HOF data. Large models, images, backups and reports
stay local. Destinations are selected by skin before a session, including AI.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from kn5_tools import Kn5, Node
from repair_omsi_bus_physics import AC, bounds
from set_kmb_bus_display import VEHICLES, read_hof

PROFILES = {
    "e200": dict(id="kmb_e200_drivable", source="ADL_E200_KMB_AAU_with_OrangePai", colour="orange", art="Anzeigen/HANOVER_ORANGE_FULL"),
    "e6m": dict(id="kmb_e6m_drivable", source="ADL_E500MMC_KMB_E6M", colour="white", art="Anzeigen/HANOVER_WHITE_FULL"),
    "atenu": dict(id="kmb_atenu_drivable", source="ADL_E500MMC_KMB_ATENU", colour="orange", art="GX7767Electronics/GX7767_Hanover_KMB_O/hanover"),
    "atee": dict(id="kmb_atee_drivable", source="ADL_Enviro500_KMB_ATEE_WV820", colour="green", art="Anzeigen/HongLong_Green"),
    "scania": dict(id="kmb_scania_k230ub_drivable", source="Scania_K230UB_KMB_ASB_ASC_4479", colour="green", art="GX7767Electronics/GX7767_Gorba_KMB_G/display_ASB"),
    "dragon": dict(id="kmb_dennis_dragon_9m_drivable", source="Dennis_Dragon 9.9M_KMB_ADS186_235", colour="rollblind", art="Anzeigen/GX7767"),
}
PRESETS = [
    ("not_in_service", "NIS", "Not in Service / 暫停服務", None),
    ("51_tai_mo_shan", "51", "Tai Mo Shan / 大帽山 巔峰之旅", "51Y_2.bmp"),
    ("51_sheung_tsuen", "51", "Sheung Tsuen / 上村", "51Z.bmp"),
    ("51_nina_tower", "51", "Tsuen Wan (Nina Tower) / 荃灣（如心廣場）", "51Y.bmp"),
]


def route_label(destination, fallback):
    match = re.match(r"^([A-Za-z0-9]+)\s+(.+)$", destination.strip())
    if not match:
        return fallback, destination
    token, text = match.groups()
    # The installed full HOF uses Y/Z/V as direction markers (51Y/51Z).
    # Preserve actual route suffixes such as A, B, M and X.
    if re.fullmatch(r"[A-Za-z]?\d+[A-UW-X]?[VYZ]", token):
        token = token[:-1]
    return token, text


def dds(image):
    stream = io.BytesIO()
    image.convert("RGBA").save(stream, format="DDS", pixel_format="DXT5")
    return stream.getvalue()


def backup_write(path, raw, backup, relative):
    if path.exists() and path.read_bytes() == raw:
        return
    if path.exists():
        dest = backup / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(path, dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def mesh(name, vertices, material):
    vertices = np.asarray(vertices, dtype="<f4")
    if len(vertices) > 65535 or len(vertices) % 3:
        raise ValueError("Invalid sign triangle count")
    indices = np.arange(len(vertices), dtype="<u2")
    payload = bytearray(struct.pack("<???I", False, True, False, len(vertices)))
    payload += vertices.tobytes() + struct.pack("<I", len(indices)) + indices.tobytes()
    payload += struct.pack("<II2f4f?", material, 0, 0., 2000., 0., 0., 0., 1., True)
    node = Node(2, name, True, payload, [], len(vertices), 7, 44, len(indices), material)
    bounds(node)
    return node


def panels(model, family):
    existing = {n.name.removeprefix("KMB_DESTINATION_").lower(): n for _, n in model.root.walk()
                if n.kind == 2 and n.name.startswith("KMB_DESTINATION_")}
    if existing:
        return existing
    selected, removed = {}, set()

    def visit(node, parent=np.eye(4)):
        world = node.matrix @ parent if node.kind == 1 else parent
        if node.kind == 2:
            name = node.name.lower()
            mat = model.materials[node.material_id]["name"].lower()
            select = ((family == "atenu" and name == "kmb_atenu_drivable_rt_m0") or
                      (family == "atee" and "_atee_rollband_" in name) or
                      (family == "scania" and "_gorbasystem_" in name) or
                      (family == "dragon" and "_rollband_kmb_" in name and
                       ("rollband_dest" in mat or "_rt_no" in mat)))
            # ATEE's unused alternative Hanover geometry otherwise covers the
            # selected HongLong panels with the initial blank textures.
            if family == "atee" and "_hanoversystem_" in name:
                removed.add(node.name)
            if select:
                removed.add(node.name)
                values = node.vertices.copy()
                values[:, :3] = values[:, :3] @ world[:3, :3] + world[3, :3]
                values[:, 3:6] = values[:, 3:6] @ world[:3, :3]
                faces = np.frombuffer(node.payload, "<u2", node.index_count,
                    node.vertex_offset + node.vertex_count * node.vertex_stride + 4).reshape(-1, 3)
                for face in faces:
                    tri = values[face].copy()
                    normal = tri[:, 3:6].mean(0)
                    if np.linalg.norm(normal) < .1:
                        normal = np.cross(tri[1, :3] - tri[0, :3], tri[2, :3] - tri[0, :3])
                    normal /= max(np.linalg.norm(normal), 1e-10)
                    panel = "front" if normal[2] > .65 else "rear" if normal[2] < -.65 else "side" if normal[0] > .65 else None
                    if panel is None:
                        continue
                    if family == "dragon" and "_rt_no" in mat:
                        panel += "_number"
                    selected.setdefault(panel, []).append(tri)
        for child in node.children:
            visit(child, world)

    visit(model.root)
    if not selected:
        raise ValueError(f"No original destination surfaces found for {family}")
    for _, parent in model.root.walk():
        parent.children = [n for n in parent.children if n.name not in removed]
    result = {}
    for face, chunks in selected.items():
        vertices = np.concatenate(chunks)
        xyz = vertices[:, :3]
        u = xyz[:, 0] if face.startswith("front") else -xyz[:, 0] if face.startswith("rear") else -xyz[:, 2]
        if np.ptp(u) < .01 or np.ptp(xyz[:, 1]) < .01:
            raise ValueError(f"Degenerate {family} {face} sign")
        vertices[:, 6] = (u - u.min()) / np.ptp(u)
        vertices[:, 7] = (xyz[:, 1].max() - xyz[:, 1]) / np.ptp(xyz[:, 1])
        name = "KMB_DESTINATION_" + face.upper()
        material = len(model.materials)
        model.materials.append(dict(name=name, shader="ksPerPixel", blend=0, alpha_test=0, depth=0,
            props={"ksAmbient": (.3,) + (0.,) * 9, "ksDiffuse": (.4,) + (0.,) * 9,
                   "ksEmissive": (0., 0., 0., .7, .7, .7, 0., 0., 0., 0.)},
            maps=[dict(name="txDiffuse", slot=0, texture=f"kmb_destination_{face}.dds")]))
        new = mesh(name, vertices, material)
        model.root.children.append(new)
        result[face] = new
    return result


def source_art(profile, family, filename):
    preferred = VEHICLES / profile["art"]
    if filename is None:
        if profile["colour"] in ("orange", "white"):
            folder = "HANOVER_ORANGE_FULL" if profile["colour"] == "orange" else "HANOVER_WHITE_FULL"
            candidate = VEHICLES / "Anzeigen" / folder / "Lantau_North/NIS.bmp"
        elif profile["colour"] == "green":
            candidate = VEHICLES / "Anzeigen/HongLong_Green/Lantau_North/NIS.bmp"
        else:
            return None, "No installed NIS rollblind artwork; rendered from route data"
        return candidate, None if profile["colour"] in ("orange", "white") or family == "atee" else "Gorba bitmap absent; installed green OMSI NIS artwork adapted"
    for directory in (preferred, preferred / "KMBVC", preferred / "Lantau_North"):
        candidate = directory / filename
        if candidate.is_file():
            return candidate, None
    if profile["colour"] == "rollblind":
        return None, "Matching rollblind bitmap absent; rendered from HOF destination text"
    shared = "HANOVER_ORANGE_FULL" if profile["colour"] == "orange" else "HANOVER_WHITE_FULL" if profile["colour"] == "white" else "HANOVER"
    candidate = VEHICLES / "Anzeigen" / shared / "KMBVC" / filename
    if candidate.is_file():
        return candidate, f"Matching {family} bitmap absent; installed {shared} artwork adapted"
    return None, "Matching OMSI bitmap absent; rendered from HOF destination text"


def crop_art(path, face):
    image = Image.open(path).convert("RGB")
    base = face.split("_")[0]
    if image.size == (512, 512):
        box = {"front": (0, 0, 416, 128), "side": (0, 144, 512, 240), "rear": (64, 256, 208, 416)}[base]
        if path.stem.upper() == "NIS" and base == "rear":
            box = (0, 256, 272, 416)
    elif image.width >= 675 and image.height in (136, 180):
        # Classic front destination plus route-only side/rear. Three-panel
        # orange Hanover atlases put the rear number after column 675.
        if base == "front":
            box = (0, 0, 416, 128)
        elif base == "rear" and image.width >= 914:
            box = (675, 0, 914, 128)
        else:
            box = (416, 0, 675, 128)
    else:
        # Original GX7767 printed destination sheets are standalone signs.
        box = (0, 0, image.width, image.height)
    return image.crop(box), list(box)


def text_art(route, destination, face, colour, size):
    canvas = Image.new("RGB", size, "black")
    number_only = "number" in face or face == "rear"
    text = route if number_only else ("暫停服務\nNOT IN SERVICE" if route == "NIS" else destination.replace(" / ", "\n"))
    if not number_only and route != "NIS" and colour != "rollblind":
        text += "  " + route
    color = {"orange": (255, 177, 0), "green": (198, 255, 54), "white": (245, 245, 245), "rollblind": (235, 228, 205)}[colour]
    draw = ImageDraw.Draw(canvas)
    font_path = "C:/Windows/Fonts/msjhbd.ttc"
    for height in range(max(16, int(size[1] * .8)), 7, -2):
        font = ImageFont.truetype(font_path, height)
        box = draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=3)
        if box[2] - box[0] < size[0] * .94 and box[3] - box[1] < size[1] * .9:
            break
    draw.multiline_text(((size[0] - box[2] + box[0]) / 2 - box[0], (size[1] - box[3] + box[1]) / 2 - box[1]),
                        text, font=font, fill=color, align="center", spacing=3)
    return canvas


def artwork(profile, family, route, destination, filename, face, size):
    path, warning = source_art(profile, family, filename)
    if "number" in face:
        path = None
        warning = "Route-number rollblind rendered from the selected route data"
    if path:
        panel, crop = crop_art(path, face)
        fitted = ImageOps.contain(panel, size, Image.Resampling.NEAREST)
        image = Image.new("RGB", size, "black")
        image.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
        origin = dict(source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), crop=crop)
    else:
        image = text_art(route, destination, face, profile["colour"], size)
        origin = dict(source="HOF/preset route text", rendered_fallback=True)
    if np.asarray(image).max() == 0:
        raise ValueError(f"Blank {family} {route} {face} artwork")
    return image, {**origin, "warning": warning, "colour": profile["colour"]}


def prepare(car, family, routes, output, install):
    profile = PROFILES[family]
    model_path = car / (car.name + ".kn5")
    model = Kn5(model_path)
    panel_nodes = panels(model, family)
    expected = {"front", "side", "rear"} if family != "dragon" else {"front", "front_number", "side_number", "rear_number"}
    if not expected.issubset(panel_nodes):
        raise ValueError(f"Missing destination faces on {family}: {expected - panel_nodes.keys()}")
    backup = output / "backups" / family
    embedded, entries = {}, []
    for skin_name, route, destination, filename in routes:
        skin = output / "cars" / car.name / "skins" / skin_name
        skin.mkdir(parents=True, exist_ok=True)
        for name in ("skin.ini", "livery.png"):
            seed = car / "skins/0_kmb" / name
            if seed.exists():
                shutil.copy2(seed, skin / name)
        for face, node in panel_nodes.items():
            values = node.vertices[:, :3]
            width = np.ptp(values[:, 0] if face.startswith(("front", "rear")) else values[:, 2])
            aspect = float(width / np.ptp(values[:, 1]))
            size = (1024, max(64, min(1536, round(1024 / aspect / 4) * 4)))
            image, origin = artwork(profile, family, route, destination, filename, face, size)
            texture = f"kmb_destination_{face}.dds"
            raw = dds(image)
            (skin / texture).write_bytes(raw)
            image.save(skin / ("sign_" + face + ".png"))
            if skin_name == "not_in_service":
                embedded[texture] = raw
            entries.append(dict(skin=skin_name, route=route, destination=destination, face=face, **origin))
        label = "KMB CUSTOM" if skin_name == "kmb_custom_route" else "KMB"
        metadata = dict(skinname=f"{label} | {route} | {destination} | {profile['colour']}", drivername="", country="Hong Kong", number=route)
        (skin / "ui_skin.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        if install:
            for path in skin.iterdir():
                if path.name.startswith("sign_"):
                    continue
                rel = Path("skins") / skin_name / path.name
                backup_write(car / rel, path.read_bytes(), backup, rel)
            if skin_name == "not_in_service":
                for path in skin.glob("*.dds"):
                    rel = Path("skins/0_kmb") / path.name
                    backup_write(car / rel, path.read_bytes(), backup, rel)
    # Use the same unique materials for original E200/E6M panels and new ones.
    for face, node in panel_nodes.items():
        mat = copy.deepcopy(model.materials[node.material_id])
        mat["name"] = "KMB_DESTINATION_" + face.upper()
        mat["props"]["ksEmissive"] = (0., 0., 0., .35, .35, .35, 0., 0., 0., 0.) if family == "dragon" else (0., 0., 0., .7, .7, .7, 0., 0., 0., 0.)
        mat["maps"] = [dict(name="txDiffuse", slot=0, texture=f"kmb_destination_{face}.dds")]
        model.materials[node.material_id] = mat
    model.rebuild_prefix(embedded)
    dest = output / "cars" / car.name / model_path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    model.write(dest)
    reread = Kn5(dest)
    if len([n for _, n in reread.root.walk() if n.name.startswith("KMB_DESTINATION_")]) != len(panel_nodes):
        raise ValueError("Duplicate/missing sign geometry after KN5 serialization")
    if install:
        backup_write(model_path, dest.read_bytes(), backup, model_path.name)
    report = dict(car=car.name, family=family, panels=list(panel_nodes), colour=profile["colour"],
                  installed=install, entries=entries, model_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                  limitations="Static skin selection; fallback artwork is explicitly recorded; no OMSI keypad scripting")
    (output / (family + "_displays.json")).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bus", choices=["all", *PROFILES], default="all")
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--hof", type=Path)
    parser.add_argument("--route", help="Route or destination search; without it installs NIS and three route 51 destinations")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--entry", type=int, help="Exact one-based HOF destination index shown by --list")
    args = parser.parse_args()
    if args.install:
        proc = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
        if '"acs.exe"' in proc.stdout.lower():
            raise SystemExit("Close AC before installing destination panels")
    hof = args.hof or VEHICLES / "ADL_E200_KMB_AAU_with_OrangePai/KMB_AllRoutes_Full.hof"
    routes = PRESETS.copy()
    if args.route or args.list or args.entry:
        items = read_hof(hof)
        matches = [(i, x) for i, x in enumerate(items, 1) if not args.route or
                   re.search(r"(?i)(?<![A-Z0-9])" + re.escape(args.route) + r"(?![A-Z0-9])",
                             " ".join(route_label(x["destination"], x["route"])))]
        if args.list:
            for i, item in matches:
                print(f"{i}: {item['route']} | {item['destination']}")
            return
        if args.entry:
            matches = [(i, item) for i, item in matches if i == args.entry]
        if len(matches) != 1:
            raise SystemExit("Choose an exact destination with --list then --entry; found " + str(len(matches)))
        index, selected = matches[0]
        route, destination = route_label(selected["destination"], selected["route"])
        filename = selected["bitmaps"][0] if selected["bitmaps"] else None
        if filename is None:
            # Distinguish a text-only service from the NIS sentinel.
            filename = "__render_from_hof__.bmp"
        routes = [("kmb_custom_route", route, destination, filename)]
    args.output.mkdir(parents=True, exist_ok=True)
    for family in PROFILES if args.bus == "all" else [args.bus]:
        car = args.ac / "content/cars" / PROFILES[family]["id"]
        result = prepare(car, family, routes, args.output, args.install)
        print(json.dumps({k: result[k] for k in ("car", "panels", "colour", "installed")}))


if __name__ == "__main__":
    main()
