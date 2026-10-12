"""Render a top-down preview of the HD map FBX.

Run with Blender (background):
    blender --background --python tools/blender/preview_hd_map.py

Output:
    build/HP1C/tin_kwong_road/hd_map_preview.png   (full overview)
    build/HP1C/tin_kwong_road/hd_map_zoom.png      (test-centre close-up)
"""

from __future__ import annotations

from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "build" / "HP1C" / "tin_kwong_road"
FBX = OUT_DIR / "hd_map.fbx"
PREVIEW = OUT_DIR / "hd_map_preview.png"
ZOOM = OUT_DIR / "hd_map_zoom.png"


def frame_camera(cam, ortho_scale: float, center: tuple[float, float]) -> None:
    cam.data.clip_start = 0.1
    cam.data.clip_end = 50_000.0
    cam.location = (center[0], center[1], 3000.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    cam.data.ortho_scale = ortho_scale


def bounds() -> tuple[tuple[float, float], float]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            for corner in obj.bound_box:
                w = obj.matrix_world @ Vector(corner)
                min_x = min(min_x, w.x)
                max_x = max(max_x, w.x)
                min_y = min(min_y, w.y)
                max_y = max(max_y, w.y)
    cx, cy = (min_x + max_x) / 2, (min_y + max_y) / 2
    size = max(max_x - min_x, max_y - min_y) * 1.05
    return (cx, cy), size


def render(scene, filepath: str, res: int) -> None:
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(filepath)
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    bpy.ops.render.render(write_still=True)


def main() -> None:
    if not FBX.exists():
        raise SystemExit(f"FBX not found: {FBX}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"

    cam_data = bpy.data.cameras.new("preview_cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("preview_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    (cx, cy), size = bounds()

    # full overview
    frame_camera(cam, size, (cx, cy))
    render(scene, PREVIEW, 1536)
    print(f"[SUCCESS] Overview rendered: {PREVIEW}")

    # close-up of the test centre (origin of the local grid)
    frame_camera(cam, 1200.0, (0.0, 0.0))
    render(scene, ZOOM, 1536)
    print(f"[SUCCESS] Zoom rendered: {ZOOM}")


if __name__ == "__main__":
    main()
