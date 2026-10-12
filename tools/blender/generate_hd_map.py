"""Generate a high-detail 1:1 driving-test map for Assetto Corsa in Blender.

Run with Blender (background):
    blender --background --python tools/blender/generate_hd_map.py

Input : build/HP1C/source/tin_kwong_hd_roads.json  (prepared by tools/prepare_hd_map.py)
Output: build/HP1C/tin_kwong_road/hd_map.fbx        (metric, 1 Blender unit = 1 m)

Performance: geometry is accumulated in plain Python lists and committed to
meshes once per material layer (not per road), so the full corridor builds
in seconds-to-minutes even with tens of thousands of segments.

Layers (Assetto Corsa material naming):
  1ROAD_ASPHALT       drivable asphalt (per road), collision via ksEditor
  1KERB_15CM          raised kerbs (15 cm)
  2ROAD_MARKINGS      centre double-yellow, lane dashes, edge lines
  2ZEBRA_CROSSINGS    zebra / pedestrian crossing stripes
  3TRAFFIC_LIGHTS     traffic signal poles at signalised junctions
  9ROAD_NAMES         (debug) road-name empty objects, visible in Blender only
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build" / "HP1C" / "source" / "tin_kwong_hd_roads.json"
OUTPUT = ROOT / "build" / "HP1C" / "tin_kwong_road" / "hd_map.fbx"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

ROAD_Z = 0.08          # surface height above world origin (m)
KERB_H = 0.15          # kerb height (m)
MARK_Z = 0.085         # markings slightly above asphalt

DEFAULT_LANE_WIDTH = 3.5

# highway -> (base width per lane, marking style)
STYLE = {
    "motorway":        (3.75, "dash"),
    "trunk":           (3.60, "dash"),
    "primary":         (3.50, "dash"),
    "secondary":       (3.40, "dash"),
    "tertiary":        (3.30, "dash"),
    "unclassified":    (3.30, "dash"),
    "residential":     (3.00, "dash"),
    "service":         (2.75, "none"),
    "living_street":   (2.75, "none"),
    "pedestrian":      (3.00, "none"),
    "footway":         (2.00, "none"),
    "cycleway":        (1.80, "none"),
    "motorway_link":   (3.50, "dash"),
    "trunk_link":      (3.50, "dash"),
    "primary_link":    (3.50, "dash"),
    "secondary_link":  (3.25, "dash"),
    "tertiary_link":   (3.00, "dash"),
    "track":           (2.50, "none"),
    "construction":    (3.00, "none"),
}

# Roads that are part of the exam network get full markings.
EXAM_ROADS = {
    "Tian Kwong Road", "天光道", "Back Cheung Road", "靠背壟道",
    "Lok Shan Road", "落山道", "Mei Shing Tong Street", "美善同道",
    "Jiangsu Street", "江蘇街", "Sheung Hong Street", "常康街",
    "Sheung Shing Street", "常盛街", "Ma Tau Wai Road", "馬頭圍道",
    "Farm Road", "農圃道", "Argyle Street", "亞皆老街",
    "Carlisle Road", "嘉齡道", "Pui Ching Road", "巴富街",
    "Shek Ku Street", "石鼓街",
}


def lane_count(tags: dict) -> int:
    lanes = tags.get("lanes")
    if lanes:
        try:
            return max(1, int(str(lanes).split(";")[0]))
        except ValueError:
            pass
    highway = tags.get("highway", "")
    return 2 if highway in {"motorway", "trunk", "primary", "secondary",
                            "tertiary", "unclassified", "residential"} else 1


def oneway(tags: dict) -> bool:
    return tags.get("oneway", "no").lower() in {"yes", "true", "1", "-1"}


def road_name(tags: dict) -> str:
    return tags.get("name") or tags.get("name:zh") or tags.get("name:en") or ""


def is_exam_road(tags: dict) -> bool:
    name = road_name(tags)
    for part in name.split(" "):
        if part in EXAM_ROADS:
            return True
    return name in EXAM_ROADS


def local_xy(lat: float, lon: float, ref: tuple[float, float]) -> tuple[float, float]:
    lat0, lon0 = ref
    m_lat = 111_320.0
    m_lon = 111_320.0 * math.cos(math.radians(lat0))
    return ((lon - lon0) * m_lon, (lat - lat0) * m_lat)


class MeshBuilder:
    """Accumulate vertices/faces and commit one mesh per layer at the end."""

    def __init__(self) -> None:
        self.layers: dict[str, dict] = {}

    def _layer(self, key: str, mat: bpy.types.Material) -> dict:
        if key not in self.layers:
            self.layers[key] = {"verts": [], "faces": [], "mat": mat}
        return self.layers[key]

    def add_strip(self, key: str, mat: bpy.types.Material,
                  center: list[Vector], half_width: float, z: float) -> None:
        layer = self._layer(key, mat)
        verts = layer["verts"]
        base = len(verts)
        for i, p in enumerate(center):
            prev = center[max(0, i - 1)]
            nxt = center[min(len(center) - 1, i + 1)]
            tan = nxt - prev
            if tan.length_squared < 1e-12:
                tan = Vector((1.0, 0.0, 0.0))
            else:
                tan.normalize()
            side = Vector((-tan.y, tan.x, 0)).normalized() * half_width
            verts.append((p.x + side.x, p.y + side.y, z))
            verts.append((p.x - side.x, p.y - side.y, z))
            if i:
                b = base + (i - 1) * 2
                layer["faces"].append((b, b + 1, b + 3, b + 2))

    def add_quad(self, key: str, mat: bpy.types.Material,
                 a: tuple, b: tuple, c: tuple, d: tuple) -> None:
        layer = self._layer(key, mat)
        base = len(layer["verts"])
        layer["verts"].extend([a, b, c, d])
        layer["faces"].append((base, base + 1, base + 2, base + 3))

    def add_box(self, key: str, mat: bpy.types.Material,
                center: tuple, size: tuple) -> None:
        cx, cy, cz = center
        sx, sy, sz = size
        x0, x1 = cx - sx / 2, cx + sx / 2
        y0, y1 = cy - sy / 2, cy + sy / 2
        z0, z1 = cz - sz / 2, cz + sz / 2
        corners = [
            (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
        ]
        faces = [
            (0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4),
            (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
        ]
        layer = self._layer(key, mat)
        base = len(layer["verts"])
        layer["verts"].extend(corners)
        layer["faces"].extend([tuple(base + i for i in f) for f in faces])

    def commit(self) -> int:
        count = 0
        for key, layer in self.layers.items():
            if not layer["verts"]:
                continue
            mesh = bpy.data.meshes.new(key + "_mesh")
            mesh.from_pydata(layer["verts"], [], layer["faces"])
            mesh.materials.append(layer["mat"])
            obj = bpy.data.objects.new(key, mesh)
            bpy.context.collection.objects.link(obj)
            count += 1
        return count


def catmull_rom(points: list[Vector], subdivisions: int = 4) -> list[Vector]:
    if len(points) < 3:
        return points
    result: list[Vector] = []
    padded = [points[0], *points, points[-1]]
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[i - 1], padded[i], padded[i + 1], padded[i + 2]
        for step in range(subdivisions):
            t = step / subdivisions
            t2, t3 = t * t, t * t * t
            result.append(0.5 * (
                (2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
            ))
    result.append(points[-1])
    return result


def dash_segments(center: list[Vector], dash_len: float = 3.0,
                  gap_len: float = 3.0) -> list[list[Vector]]:
    """Split a centreline into dash segments (for lane markings)."""
    segments: list[list[Vector]] = []
    current: list[Vector] = []
    travelled = 0.0
    for i in range(len(center) - 1):
        a, b = center[i], center[i + 1]
        seg_len = (b - a).length
        steps = max(2, int(seg_len / 1.0))
        for s in range(1, steps + 1):
            p = a.lerp(b, s / steps)
            travelled += seg_len / steps
            if not current or (current[-1] - p).length > 0.05:
                current.append(p)
            if travelled >= dash_len + gap_len:
                travelled = 0.0
                if len(current) > 1:
                    segments.append(current)
                current = []
    if len(current) > 1:
        segments.append(current)
    return segments


def build() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Source extract not found: {SOURCE}\n"
                         "Run: python tools/prepare_hd_map.py first.")

    with open(SOURCE, "r", encoding="utf-8") as f:
        data = json.load(f)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1.0

    def mat(name: str, color: tuple) -> bpy.types.Material:
        m = bpy.data.materials.new(name)
        m.diffuse_color = color
        return m

    asphalt = mat("HK_asphalt", (0.05, 0.055, 0.06, 1))
    asphalt_dark = mat("HK_asphalt_dark", (0.04, 0.045, 0.05, 1))
    kerb_mat = mat("HK_kerb", (0.45, 0.45, 0.46, 1))
    line_yellow = mat("HK_line_yellow", (0.85, 0.75, 0.12, 1))
    line_white = mat("HK_line_white", (0.92, 0.92, 0.90, 1))
    zebra_white = mat("HK_zebra_white", (0.95, 0.95, 0.93, 1))
    tl_pole = mat("tl_pole", (0.25, 0.25, 0.25, 1))
    tl_head = mat("tl_head", (0.1, 0.1, 0.1, 1))

    mb = MeshBuilder()
    ref = (float(data["reference"]["lat"]), float(data["reference"]["lon"]))
    elements = data["elements"]
    print(f"[INFO] Building {len(elements)} ways from {SOURCE.name}")

    road_count = 0
    crossing_points: list[tuple[Vector, int]] = []
    signal_junctions: list[Vector] = []

    for idx, el in enumerate(elements):
        tags = el.get("tags", {})
        highway = tags.get("highway", "")
        if highway not in STYLE:
            continue
        base_width, mark_style = STYLE[highway]
        lanes = lane_count(tags)
        one_way = oneway(tags)

        pts = [Vector((*local_xy(p["lat"], p["lon"], ref), ROAD_Z))
               for p in el["geometry"]]
        if len(pts) < 2:
            continue
        smooth = catmull_rom(pts, subdivisions=4)

        # --- carriageway ------------------------------------------------------
        if one_way:
            strips = [(smooth, 0.0)]
        else:
            strips = []
            for direction in (-1, 1):
                off = direction * (base_width * 0.5)
                centre = [Vector((p.x + off, p.y, p.z)) for p in smooth]
                strips.append((centre, direction))

        for centre, _dir in strips:
            mb.add_strip("1ROAD_ASPHALT",
                         asphalt_dark if highway in {"trunk", "motorway"} else asphalt,
                         centre, base_width / 2, ROAD_Z)
            for side in (-1, 1):
                kerb_pts = [Vector((p.x + side * (base_width / 2 + 0.12), p.y, p.z))
                            for p in centre]
                mb.add_strip("1KERB_15CM", kerb_mat, kerb_pts, 0.12, ROAD_Z)

        # --- markings -----------------------------------------------------------
        edge = base_width / 2
        if mark_style == "dash":
            if not one_way:
                for side in (-0.12, 0.12):
                    centre_line = [Vector((p.x + side, p.y, MARK_Z)) for p in smooth]
                    mb.add_strip("2ROAD_MARKINGS_YELLOW", line_yellow,
                                 centre_line, 0.10, MARK_Z)
                for side in (-1, 1):
                    edge_line = [Vector((p.x + side * (edge - 0.15), p.y, MARK_Z))
                                 for p in smooth]
                    mb.add_strip("2ROAD_MARKINGS_EDGE", line_white,
                                 edge_line, 0.10, MARK_Z)
                for lane_i in range(1, lanes):
                    off = (lane_i - lanes / 2) * DEFAULT_LANE_WIDTH
                    if abs(off) < 0.25:
                        continue
                    lane_line = [Vector((p.x + off, p.y, MARK_Z)) for p in smooth]
                    for dash in dash_segments(lane_line):
                        mb.add_strip("2ROAD_MARKINGS_DASH", line_white,
                                     dash, 0.10, MARK_Z)
            else:
                for side in (-1, 1):
                    edge_line = [Vector((p.x + side * (edge - 0.15), p.y, MARK_Z))
                                 for p in smooth]
                    mb.add_strip("2ROAD_MARKINGS_EDGE", line_white,
                                 edge_line, 0.10, MARK_Z)
                for lane_i in range(1, lanes):
                    off = (lane_i - lanes / 2) * DEFAULT_LANE_WIDTH
                    lane_line = [Vector((p.x + off, p.y, MARK_Z)) for p in smooth]
                    for dash in dash_segments(lane_line):
                        mb.add_strip("2ROAD_MARKINGS_DASH", line_white,
                                     dash, 0.10, MARK_Z)

        # --- crossings / signals ------------------------------------------------
        crossing = tags.get("crossing")
        if crossing and crossing != "no":
            mid = smooth[len(smooth) // 2]
            crossing_points.append((mid, lanes))
        if tags.get("traffic_signals"):
            mid = smooth[len(smooth) // 2]
            signal_junctions.append(mid)

        road_count += 1
        if idx % 1000 == 0:
            print(f"  ... {idx}/{len(elements)} ways processed")

    # zebra crossings (rotated stripes around crossing centre)
    for i, (loc, lanes) in enumerate(crossing_points[:120]):
        angle = (i * 47) % 180 - 90
        width = lanes * DEFAULT_LANE_WIDTH
        rad = math.radians(angle)
        u = Vector((math.cos(rad), math.sin(rad), 0))
        v = Vector((-u.y, u.x, 0))
        n = max(4, int((width + 2.0) / 0.6))
        for k in range(n):
            off = (k - n / 2) * 0.6
            c = loc + u * off
            half_l = (width + 1.2) / 2
            a = c + v * half_l + u * 0.22
            b = c + v * half_l - u * 0.22
            d = c - v * half_l - u * 0.22
            e = c - v * half_l + u * 0.22
            mb.add_quad("2ZEBRA_CROSSINGS", zebra_white,
                        (a.x, a.y, MARK_Z + 0.005), (b.x, b.y, MARK_Z + 0.005),
                        (d.x, d.y, MARK_Z + 0.005), (e.x, e.y, MARK_Z + 0.005))

    # traffic light poles
    for loc in signal_junctions[:40]:
        mb.add_box("3TRAFFIC_LIGHTS", tl_pole, (loc.x, loc.y, 2.1), (0.12, 0.12, 4.2))
        mb.add_box("3TRAFFIC_LIGHTS", tl_head, (loc.x, loc.y, 4.0), (0.5, 0.25, 1.2))
        for i, col in enumerate([(0.95, 0.1, 0.1, 1), (0.95, 0.6, 0.05, 1), (0.05, 0.9, 0.1, 1)]):
            light_mat = mat("tl_lamp_%d" % i, col)
            mb.add_box("3TRAFFIC_LIGHTS", light_mat,
                       (loc.x, loc.y + 0.13, 4.35 - i * 0.4), (0.16, 0.02, 0.16))

    # exam-route road names as debug empties
    for el in elements:
        tags = el.get("tags", {})
        if not is_exam_road(tags):
            continue
        pts = el["geometry"]
        if len(pts) >= 2:
            mid = pts[len(pts) // 2]
            x, y = local_xy(mid["lat"], mid["lon"], ref)
            empty = bpy.data.objects.new("9ROAD_NAME_" + road_name(tags).replace(" ", "_"), None)
            empty.empty_display_size = 0.5
            empty.location = (x, y, 3.0)
            bpy.context.collection.objects.link(empty)

    layers = mb.commit()
    print(f"[INFO] {road_count} roads, {len(crossing_points)} crossings, "
          f"{len(signal_junctions)} signal junctions, {layers} mesh layers")

    bpy.ops.export_scene.fbx(filepath=str(OUTPUT), use_selection=False,
                             axis_forward="-Z", axis_up="Y")
    print(f"[SUCCESS] Exported {OUTPUT}")


if __name__ == "__main__":
    build()
