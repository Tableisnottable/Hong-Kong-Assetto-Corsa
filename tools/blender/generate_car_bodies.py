"""Generate 1:1 procedural 3D car bodies for all 6 HK exam vehicles in Blender.

Run with Blender (background):
    blender --background --python tools/blender/generate_car_bodies.py

Output per car (in content/cars/<car_id>/):
    body.fbx          1:1 metric car body (gitignored, for ksEditor KN5 conversion)
    preview.png       top-down + side preview render (committed)

Body style per vehicle type:
  - hatchback (Yaris, Prius): 5-door hatchback silhouette
  - van (HiAce x2): cab-over box van silhouette
  - bus (E500 x2): double-decker bus silhouette

All dimensions from car/driving test car/ spec sheets (meters, 1 unit = 1 m).
Origin at ground center, +Y forward, +Z up (Blender convention).
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
CARS_DIR = ROOT / "content" / "cars"

# (car_id, style, length, width, height, wheelbase, wheel_dia, extra)
CARS = [
    ("hk_cat1_toyota_yaris", "hatchback", 3.950, 1.695, 1.510, 2.510, 0.634, {}),
    ("hk_cat1a_toyota_prius", "hatchback", 4.540, 1.760, 1.470, 2.700, 0.634, {}),
    ("hk_cat2_toyota_hiace_mt", "van", 4.695, 1.695, 1.980, 2.570, 0.660, {}),
    ("hk_cat2a_toyota_hiace_at", "van", 4.695, 1.695, 1.980, 2.570, 0.660, {}),
    ("hk_cat17_adl_e500_gen1", "bus", 12.000, 2.550, 4.300, 5.950, 1.020, {"decks": 2}),
    ("hk_cat17a_adl_e500_mmc", "bus", 12.000, 2.550, 4.347, 5.980, 1.020, {"decks": 2}),
]


def mat(name: str, color: tuple) -> bpy.types.Material:
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    return m


class Builder:
    def __init__(self) -> None:
        self.verts: list = []
        self.faces: list = []

    def box(self, cx: float, cy: float, cz: float,
            sx: float, sy: float, sz: float) -> None:
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        c = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
             (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
             (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
             (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
        b = len(self.verts)
        self.verts.extend(c)
        self.faces.extend([
            (b, b + 1, b + 2, b + 3), (b + 4, b + 5, b + 6, b + 7),
            (b, b + 4, b + 7, b + 3), (b + 1, b + 5, b + 6, b + 2),
            (b + 3, b + 2, b + 6, b + 7), (b, b + 1, b + 5, b + 4),
        ])

    def wheel(self, cx: float, cy: float, cz: float, radius: float,
              width: float, segments: int = 16) -> None:
        # cylinder axis along X (axle direction)
        b = len(self.verts)
        for ring in (cx - width / 2, cx + width / 2):
            for i in range(segments):
                a = 2 * math.pi * i / segments
                self.verts.append((ring, cy + radius * math.cos(a),
                                   cz + radius * math.sin(a)))
        for i in range(segments):
            j = (i + 1) % segments
            self.faces.append((b + i, b + j, b + segments + j, b + segments + i))
        # caps
        cap_c0 = len(self.verts)
        self.verts.append((cx - width / 2, cy, cz))
        cap_c1 = len(self.verts)
        self.verts.append((cx + width / 2, cy, cz))
        for i in range(segments):
            j = (i + 1) % segments
            self.faces.append((cap_c0, b + j, b + i))
            self.faces.append((cap_c1, b + segments + i, b + segments + j))

    def commit(self, name: str, material: bpy.types.Material) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(name + "_mesh")
        mesh.from_pydata(self.verts, [], self.faces)
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        return obj


def build_hatchback(b: Builder, wb: Builder, length: float, width: float,
                    height: float, wheelbase: float, wheel_dia: float) -> None:
    ground = wheel_dia / 2
    # lower body
    b.box(0, 0, ground + 0.35, width, length * 0.92, 0.70)
    # cabin / greenhouse (tapered look via smaller box)
    b.box(0, -length * 0.03, ground + 0.35 + 0.35 + 0.28,
          width * 0.88, length * 0.52, 0.56)
    # hood slope hint
    b.box(0, length * 0.32, ground + 0.62, width * 0.92, length * 0.22, 0.18)
    # wheels
    wr = wheel_dia / 2
    fx, rx = wheelbase / 2, -wheelbase / 2
    for sx in (-1, 1):
        wb.wheel(sx * (width / 2 - 0.10), fx, wr, wr, 0.20)
        wb.wheel(sx * (width / 2 - 0.10), rx, wr, wr, 0.20)


def build_van(b: Builder, wb: Builder, length: float, width: float,
              height: float, wheelbase: float, wheel_dia: float) -> None:
    ground = wheel_dia / 2
    # main box body (cab-over van)
    b.box(0, -length * 0.04, ground + (height - ground) / 2,
          width, length * 0.94, height - ground)
    # windshield slope hint
    b.box(0, length * 0.40, ground + 1.05, width * 0.94, 0.35, 0.55)
    # wheels
    wr = wheel_dia / 2
    fx, rx = wheelbase / 2, -wheelbase / 2
    for sx in (-1, 1):
        wb.wheel(sx * (width / 2 - 0.10), fx, wr, wr, 0.22)
        wb.wheel(sx * (width / 2 - 0.10), rx, wr, wr, 0.22)


def build_bus(b: Builder, wb: Builder, length: float, width: float,
              height: float, wheelbase: float, wheel_dia: float) -> None:
    ground = wheel_dia / 2
    # lower deck
    deck_h = (height - ground) / 2
    b.box(0, 0, ground + deck_h / 2, width, length * 0.97, deck_h)
    # upper deck
    b.box(0, -length * 0.01, ground + deck_h + deck_h / 2,
          width * 0.98, length * 0.95, deck_h)
    # windshield
    b.box(0, length * 0.46, ground + 1.35, width * 0.92, 0.30, 1.10)
    # wheels: front axle + drive axle + trailing axle (6x2)
    wr = wheel_dia / 2
    fx = wheelbase / 2
    dx = -wheelbase / 2
    tx = dx - 1.60
    for sx in (-1, 1):
        wb.wheel(sx * (width / 2 - 0.12), fx, wr, wr, 0.28)
        wb.wheel(sx * (width / 2 - 0.12), dx, wr, wr, 0.28)
        wb.wheel(sx * (width / 2 - 0.12), tx, wr * 0.9, wr * 0.9, 0.26)


def render_preview(scene, cam, out_path: str, res: int = 1024) -> None:
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = out_path
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    bpy.ops.render.render(write_still=True)


def build_one(car_id: str, style: str, length: float, width: float,
              height: float, wheelbase: float, wheel_dia: float,
              extra: dict) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    body_mat = mat("car_body", (0.75, 0.08, 0.08, 1))  # exam red
    glass_mat = mat("car_glass", (0.15, 0.20, 0.28, 1))
    tyre_mat = mat("car_tyre", (0.05, 0.05, 0.05, 1))
    trim_mat = mat("car_trim", (0.55, 0.55, 0.58, 1))

    body = Builder()
    wheels = Builder()
    glass = Builder()

    if style == "hatchback":
        build_hatchback(body, wheels, length, width, height, wheelbase, wheel_dia)
        glass.box(0, -length * 0.03, wheel_dia / 2 + 0.35 + 0.35 + 0.28,
                  width * 0.80, length * 0.44, 0.40)
    elif style == "van":
        build_van(body, wheels, length, width, height, wheelbase, wheel_dia)
        glass.box(0, length * 0.40, wheel_dia / 2 + 1.05,
                  width * 0.86, 0.28, 0.42)
    else:
        build_bus(body, wheels, length, width, height, wheelbase, wheel_dia)
        # window bands both decks
        deck_h = (height - wheel_dia / 2) / 2
        glass.box(0, 0, wheel_dia / 2 + deck_h * 0.62,
                  width * 1.005, length * 0.90, deck_h * 0.42)
        glass.box(0, -length * 0.01, wheel_dia / 2 + deck_h * 1.62,
                  width * 0.985, length * 0.88, deck_h * 0.42)

    body.commit("CAR_BODY", body_mat)
    wheels.commit("CAR_WHEELS", tyre_mat)
    glass.commit("CAR_GLASS", glass_mat)

    out_dir = CARS_DIR / car_id
    out_dir.mkdir(parents=True, exist_ok=True)
    fbx_path = out_dir / "body.fbx"
    bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=False,
                             axis_forward="-Z", axis_up="Y")
    print(f"[OK] {car_id}: exported {fbx_path}")

    # preview render (workbench, 3/4 view)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    cam_data = bpy.data.cameras.new("preview_cam")
    cam_data.type = "PERSP"
    cam_data.lens = 50
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new("preview_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dist = max(length, width, height) * 1.6 + 3.0
    cam.location = (dist * 0.8, -dist, height * 0.9 + 1.0)
    # look at center
    direction = Vector((0, 0, height * 0.4)) - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    render_preview(scene, cam, str(out_dir / "preview.png"))
    print(f"[OK] {car_id}: preview rendered")


def main() -> None:
    for spec in CARS:
        build_one(*spec)
    print(f"[DONE] Built {len(CARS)} car bodies.")


if __name__ == "__main__":
    main()
