# -*- coding: utf-8 -*-
"""Generate surfaces.ini from the actual materials in each track KN5.

Assetto Corsa binds physics to geometry by matching the KN5 material name to
a `KEY=` entry in surfaces.ini. Our maps only had a single `ROAD` key while
the KN5 uses HK_asphalt / HK_kerb / HK_grass / HK_building_*, so grass had
road grip and buildings were drivable.

Usage:
    python tools/gen_track_surfaces.py
    python tools/gen_track_surfaces.py hong_kong_1to1
"""

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ROOT / "content" / "tracks"

CENTRE_BY_TRACK = {
    "hong_kong_1to1": "tin_kwong_road",
    "hong_kong_1to1_sheung_on": "sheung_on_street",
    "hong_kong_1to1_texaco": "texaco_road",
    "hong_kong_1to1_happy_valley": "happy_valley",
    "hong_kong_1to1_so_kun_po": "so_kun_po",
    "hong_kong_1to1_shek_am": "shek_am",
    "hong_kong_1to1_yau_tong": "yau_tong",
    "hong_kong_1to1_chung_ngai": "chung_ngai_street",
    "hong_kong_1to1_pui_ching": "pui_ching_road",
    "hong_kong_1to1_wing_hau": "wing_hau_street",
    "hong_kong_1to1_ap_lei_chau": "ap_lei_chau",
    "hong_kong_1to1_yuen_long": "yuen_long",
    "hong_kong_1to1_sha_tin": "sha_tin",
}

# Physics per material family. Values follow Kunos convention.
# friction: 0.98 asphalt, 0.99 painted lines, 0.85 grass, kerbs ~0.95.
SURFACE_DEFS = {
    "asphalt": dict(friction=0.98, damping=0.0, wav="", pitch=0, ff="NULL",
                    dirt=0, valid=1, vibration_gain=0.0, vibration_length=0.0),
    "asphalt_dark": dict(friction=0.98, damping=0.0, wav="", pitch=0, ff="NULL",
                         dirt=0, valid=1, vibration_gain=0.0, vibration_length=0.0),
    "kerb": dict(friction=0.95, damping=0.1, wav="kerb.wav", pitch=1.3, ff=1,
                 dirt=0, valid=0, vibration_gain=0.1, vibration_length=0.2),
    "line_white": dict(friction=0.99, damping=0.0, wav="", pitch=0, ff="NULL",
                       dirt=0, valid=1, vibration_gain=0.02, vibration_length=0.1),
    "line_yellow": dict(friction=0.99, damping=0.0, wav="", pitch=0, ff="NULL",
                        dirt=0, valid=1, vibration_gain=0.02, vibration_length=0.1),
    "zebra_white": dict(friction=0.99, damping=0.0, wav="", pitch=0, ff="NULL",
                        dirt=0, valid=1, vibration_gain=0.02, vibration_length=0.1),
    "grass": dict(friction=0.62, damping=0.35, wav="grass.wav", pitch=1.0, ff="NULL",
                  dirt=6, valid=0, vibration_gain=0.0, vibration_length=0.0),
    "building": dict(friction=0.40, damping=0.9, wav="", pitch=0, ff="NULL",
                     dirt=10, valid=0, vibration_gain=0.6, vibration_length=0.9),
    "tree": dict(friction=0.45, damping=0.8, wav="", pitch=0, ff="NULL",
                 dirt=8, valid=0, vibration_gain=0.5, vibration_length=0.9),
    "default": dict(friction=0.90, damping=0.2, wav="", pitch=0, ff="NULL",
                    dirt=2, valid=0, vibration_gain=0.05, vibration_length=0.2),
}


def classify(material: str) -> str:
    name = material.lower()
    if "building" in name:
        return "building"
    if "tree" in name:
        return "tree"
    if "grass" in name:
        return "grass"
    if "zebra" in name:
        return "zebra_white"
    if "line_white" in name:
        return "line_white"
    if "line_yellow" in name:
        return "line_yellow"
    if "kerb" in name:
        return "kerb"
    if "dark" in name and "asphalt" in name:
        return "asphalt_dark"
    if "asphalt" in name:
        return "asphalt"
    return "default"


def read_material_names(path: Path) -> list[str]:
    data = path.read_bytes()
    off = [6]

    def i32():
        v = struct.unpack_from("<i", data, off[0])[0]
        off[0] += 4
        return v

    def s():
        n = i32()
        v = data[off[0]:off[0] + n].decode("utf-8", "replace")
        off[0] += n
        return v

    i32(); i32()  # version, v6 extra
    n_textures = i32()
    for _ in range(n_textures):
        if i32() == 0:
            continue
        s()
        size = i32()
        off[0] += size

    names = []
    n_materials = i32()
    for _ in range(n_materials):
        names.append(s())      # material name
        s()                     # shader
        off[0] += 1             # blend mode (u8)
        off[0] += 1             # alpha tested (u8)
        i32()                   # reserved
        n_props = i32()
        for _ in range(n_props):
            s()
            off[0] += 40
        n_samplers = i32()
        for _ in range(n_samplers):
            s(); i32(); s()
    return names


def build_ini(materials: list[str]) -> str:
    # AC matches surfaces.ini KEY against the KN5 material name, so each real
    # material needs its own entry with its exact name.
    entries = []  # (material_name, surface_kind)
    seen = set()
    for material in materials:
        if material in seen:
            continue
        seen.add(material)
        entries.append((material, classify(material)))

    kinds = {kind for _, kind in entries}
    # ROAD must always exist for AC to accept the track.
    if "asphalt" not in kinds:
        entries.insert(0, ("HK_asphalt", "asphalt"))

    lines = [
        "; Generated by tools/gen_track_surfaces.py",
        "; KEY matches the KN5 material name so AC applies the right physics.",
        "",
    ]
    for index, (material, kind) in enumerate(entries):
        d = SURFACE_DEFS[kind]
        lines += [
            f"[SURFACE_{index}]",
            f"KEY={material}",
            f"FRICTION={d['friction']}",
            f"DAMPING={d['damping']}",
            f"WAV={d['wav']}",
            f"WAV_PITCH={d['pitch']}",
            f"FF_EFFECT={d['ff']}",
            f"DIRT_ADDITIVE={d['dirt']}",
            "BLACK_FLAG_TIME=0",
            f"IS_VALID_TRACK={d['valid']}",
            "SIN_HEIGHT=0",
            "SIN_LENGTH=0",
            "IS_PITLANE=0",
            f"VIBRATION_GAIN={d['vibration_gain']}",
            f"VIBRATION_LENGTH={d['vibration_length']}",
            "",
        ]
    lines += ["[_SCRIPTING_PHYSICS]", "ALLOW_NEW_MODE_SCRIPTS=1", ""]
    return "\n".join(lines)


def main() -> None:
    targets = sys.argv[1:]
    for track in sorted(TRACKS.glob("hong_kong_1to1*")):
        if not track.is_dir() or (targets and track.name not in targets):
            continue
        kn5 = ROOT / "build" / "HP1C" / CENTRE_BY_TRACK[track.name] / "hd_map.kn5"
        if not kn5.exists():
            print(f"[skip] {track.name}: KN5 missing")
            continue
        materials = read_material_names(kn5)
        ini = build_ini(materials)
        out = track / "data" / "surfaces.ini"
        out.write_text(ini, encoding="utf-8")
        keys = [ln.split("=", 1)[1] for ln in ini.splitlines() if ln.startswith("KEY=")]
        print(f"[OK] {track.name}: {len(keys)} surfaces {keys}")


if __name__ == "__main__":
    main()
