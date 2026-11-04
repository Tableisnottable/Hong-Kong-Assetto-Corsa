# -*- coding: utf-8 -*-
"""Generate a simple box collider.kn5 for every exam car.

Writes a single box mesh matching the car's overall dimensions (from
cars_manifest.json) using the same KN5 v6 layout as export_kn5_direct.py.

Usage:
    python tools/gen_car_colliders.py
"""

import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARS = ROOT / "content" / "cars"


def write_string(f, s: str) -> None:
    data = s.encode("utf-8")
    f.write(struct.pack("<i", len(data)))
    f.write(data)


def solid_png(r=180, g=180, b=180, a=255) -> bytes:
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixels = zlib.compress(bytes((0, r, g, b, a)))
    return sig + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def write_box_kn5(path: Path, length: float, width: float, height: float) -> None:
    hl, hw, hh = length / 2, width / 2, height / 2
    corners = [
        (-hw, 0.0, -hl), (hw, 0.0, -hl), (hw, 0.0, hl), (-hw, 0.0, hl),
        (-hw, height, -hl), (hw, height, -hl), (hw, height, hl), (-hw, height, hl),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3),          # floor
        (4, 6, 5), (4, 7, 6),          # roof
        (0, 4, 5), (0, 5, 1),          # side
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    ]
    verts = []
    for i, (x, y, z) in enumerate(corners):
        # Simple outward normal approximations are fine for a collider.
        nx = 0.0 if abs(x) < hw - 1e-6 else (1.0 if x > 0 else -1.0)
        nz = 0.0 if abs(z) < hl - 1e-6 else (1.0 if z > 0 else -1.0)
        ny = 1.0 if y > hh else -1.0
        ln = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
        verts.append(((x, y, z), (nx / ln, ny / ln, nz / ln), (0.0, 0.0), (1.0, 0.0, 0.0)))

    indices = [i for face in faces for i in face]
    cx = 0.0
    cy = hh
    cz = 0.0
    radius = (hw * hw + hh * hh + hl * hl) ** 0.5

    with open(path, "wb") as f:
        f.write(b"sc6969")
        f.write(struct.pack("<i", 6))
        f.write(struct.pack("<i", 0))
        # textures
        f.write(struct.pack("<i", 1))
        f.write(struct.pack("<i", 1))
        write_string(f, "collider.png")
        png = solid_png()
        f.write(struct.pack("<i", len(png)))
        f.write(png)
        # materials
        f.write(struct.pack("<i", 1))
        write_string(f, "COLLIDER")
        write_string(f, "ksPerPixel")
        f.write(struct.pack("<2B", 0, 0))
        f.write(struct.pack("<i", 0))
        f.write(struct.pack("<i", 1))
        write_string(f, "ksAmbient")
        f.write(struct.pack("<f", 0.5))
        f.write(b"\x00" * 36)
        f.write(struct.pack("<i", 1))
        write_string(f, "txDiffuse")
        f.write(struct.pack("<i", 0))
        write_string(f, "collider.png")
        # root dummy
        f.write(struct.pack("<i", 1))
        write_string(f, "COLLIDER_ROOT")
        f.write(struct.pack("<i", 1))
        for row in range(4):
            for col in range(4):
                f.write(struct.pack("<f", 1.0 if row == col else 0.0))
        # mesh node
        f.write(struct.pack("<i", 2))
        write_string(f, "COLLIDER_BOX")
        f.write(struct.pack("<i", 0))
        f.write(struct.pack("<3B", 0, 1, 1))
        f.write(struct.pack("<i", len(verts)))
        for pos, normal, uv, tangent in verts:
            f.write(struct.pack("<3f3f2f3f", *pos, *normal, *uv, *tangent))
        f.write(struct.pack("<i", len(indices)))
        for i in range(0, len(indices), 3):
            f.write(struct.pack("<3H", indices[i], indices[i + 1], indices[i + 2]))
        f.write(struct.pack("<i", 0))
        f.write(struct.pack("<i", 0))
        f.write(struct.pack("<f", 0.0))
        f.write(struct.pack("<3f", cx, cy, cz))
        f.write(struct.pack("<f", radius))
        f.write(struct.pack("<f", 0.0))


def main() -> None:
    manifest = json.loads((CARS / "cars_manifest.json").read_text(encoding="utf-8"))
    for car in manifest["vehicles"]:
        car_id = car["id"]
        dims = car.get("dimensions_m") or []
        if isinstance(dims, dict):
            length = float(dims.get("length", 4.5))
            width = float(dims.get("width", 1.8))
            height = float(dims.get("height", 1.5))
        elif len(dims) >= 3:
            length, width, height = (float(dims[0]), float(dims[1]), float(dims[2]))
        else:
            length, width, height = 4.5, 1.8, 1.5
        out = CARS / car_id / "collider.kn5"
        if not out.parent.is_dir():
            print(f"[skip] {car_id}: folder missing")
            continue
        write_box_kn5(out, length, width, height)
        print(f"[OK] {car_id}: collider {length}x{width}x{height} m -> {out.stat().st_size} B")


if __name__ == "__main__":
    main()
