"""Build/render a separate geographic building-review scene in Blender.

Run with Blender --background --factory-startup --python this_script.py.
The scene is an authoring reference, not an exported or installed game track.
"""
from pathlib import Path
import json
import math
import sys

import bpy
from mathutils import Vector
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from research_quality_sources import save
from collect_build_data import digest

OUTPUT = ROOT / "gis/building_review"
RENDERS = ROOT / "previews/building_review"
ORIGIN = np.array([826000., 833000.])


def material(name, color, image=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = .9
    bsdf.inputs["Metallic"].default_value = 0
    if image:
        texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.image = bpy.data.images.load(str(image), check_existing=True)
        texture.image.pack()
        mat.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def mesh_object(name, vertices, faces, collection, mat, uv=None, colors=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices.tolist(), [], faces.tolist())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(mat)
    indices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", indices)
    if uv is not None:
        mesh.uv_layers.new(name="UVMap").uv.foreach_set("vector", uv[indices].ravel())
    if colors is not None:
        if colors.shape[1] == 3:
            colors = np.column_stack((colors, np.ones(len(colors))))
        layer = mesh.color_attributes.new(name="SOURCE_COLOR", type="FLOAT_COLOR", domain="CORNER")
        layer.data.foreach_set("color", colors[indices].ravel())
        vertex_color = mat.node_tree.nodes.new("ShaderNodeVertexColor")
        vertex_color.layer_name = "SOURCE_COLOR"
        mat.node_tree.links.new(vertex_color.outputs["Color"], mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    return obj


def curve_object(name, points, radius, collection, mat):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 0
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, xyz in zip(spline.points, points):
        point.co = (*xyz, 1.)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    curve.materials.append(mat)
    return obj


def main():
    RENDERS.mkdir(parents=True, exist_ok=True)
    (ROOT / "blender").mkdir(exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.preferences.filepaths.save_version = 0
    prepared_path = OUTPUT / "prepared.json"
    prepared = json.loads(prepared_path.read_text(encoding="utf-8"))
    scene = bpy.context.scene
    collections = {}
    for name in ("REFERENCE_TERRAIN", "CLEAN_BUILDING_CANDIDATES", "TEXTURED_BUILDING_REFERENCES", "NATIVE_GENERIC_REFERENCE", "REVIEW_OUTLINES", "ROAD_REFERENCE"):
        collection = bpy.data.collections.new(name)
        scene.collection.children.link(collection)
        collections[name] = collection
    with np.load(ROOT / "gis/high_quality_pilot/pilot_dtm_05m.npz") as source:
        dtm = source["z"].copy()
        cell = float(source["cell_m"])
        west, north = float(source["west_edge"]), float(source["north_edge"])
    def terrain(e, n):
        col = np.clip(int((e - west) / cell), 0, dtm.shape[1] - 1)
        row = np.clip(int((north - n) / cell), 0, dtm.shape[0] - 1)
        return float(dtm[row, col])
    rows = np.unique(np.r_[np.arange(0, dtm.shape[0], 4), dtm.shape[0] - 1])
    cols = np.unique(np.r_[np.arange(0, dtm.shape[1], 4), dtm.shape[1] - 1])
    cc, rr = np.meshgrid(cols, rows)
    east, northings = west + (cc + .5) * cell, north - (rr + .5) * cell
    vertices = np.column_stack((east.ravel() - ORIGIN[0], northings.ravel() - ORIGIN[1], dtm[rr, cc].ravel()))
    width = len(cols)
    faces = []
    for r in range(len(rows) - 1):
        for c in range(width - 1):
            a = r * width + c
            faces.extend([(a, a + width, a + 1), (a + 1, a + width, a + width + 1)])
    photo = material("ORTHOPHOTO_LAYOUT_REFERENCE", (.7, .7, .7, 1), ROOT / "gis/high_quality_pilot/pilot_orthophoto.jpg")
    bounds = json.loads((ROOT / "reports/map_data_acquisition.json").read_text())["bounds_epsg2326"]
    uv = np.column_stack(((east.ravel() - bounds[0]) / (bounds[2] - bounds[0]),
                          (northings.ravel() - bounds[1]) / (bounds[3] - bounds[1])))
    ground = mesh_object("REFERENCE_DTM_2M_DISPLAY", vertices, np.asarray(faces), collections["REFERENCE_TERRAIN"], photo, uv=uv)
    ground["purpose"] = "Native source display subsampled to about 2m; not a driving surface"
    ground["native_sample_spacing_m"] = .5
    source_models = []
    for model in prepared["models"]:
        collection = collections["CLEAN_BUILDING_CANDIDATES" if model["variant"] == "clean" else "TEXTURED_BUILDING_REFERENCES"]
        for index, part in enumerate(model["parts"]):
            with np.load(OUTPUT / part["mesh"]) as arrays:
                vertices, faces = arrays["vertices"], arrays["faces"]
                uv = arrays["uv"] if "uv" in arrays else None
                colors = arrays["colors"] if "colors" in arrays and not part["texture"] else None
                mat = material(f"{model['variant']}_{model['model_id']}_{index}", part["base_color"],
                               ROOT / part["texture"] if part["texture"] else None)
                obj = mesh_object(f"{model['variant']}_{model['model_id']}_{index}", vertices, faces, collection, mat, uv, colors)
            obj["source_file"] = model["source_file"]
            obj["building_object_id"] = model["building_object_id"]
            obj["source_gltf_sha256"] = model["source_gltf_sha256"]
            obj["review_flags"] = json.dumps(model["flags"])
            obj["native_base_m"] = model["native_base_m"]
            obj["native_top_m"] = model["native_top_m"]
            obj["geometry_role"] = "Visual review candidate; no game collision"
            source_models.append(obj)
    generic_path = OUTPUT / "generic_prepared.json"
    generic_count = 0
    if generic_path.exists():
        generic = json.loads(generic_path.read_text(encoding="utf-8"))
        for part in generic["models"]:
            with np.load(OUTPUT / part["mesh"]) as arrays:
                mat = material(part["name"], part["base_color"], ROOT / part["texture"] if part["texture"] else None)
                obj = mesh_object(part["name"], arrays["vertices"], arrays["faces"], collections["NATIVE_GENERIC_REFERENCE"],
                                  mat, arrays["uv"] if "uv" in arrays else None)
            obj["source_file"] = part["source_file"]
            obj["source_category"] = "GENERIC"
            obj["native_heights_preserved"] = True
            obj["geometry_role"] = "Native source reference; rough structures/ground/vegetation; not finished scenery"
            generic_count += 1
    matched = {m["building_object_id"] for m in prepared["models"]}
    warning = material("MISSING_CANDIDATE_FOOTPRINT", (1., .45, .03, 1.))
    match_mat = material("MATCHED_FOOTPRINT", (.05, .55, .9, 1.))
    for feature in prepared["nearby_building_footprints"]:
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        for index, polygon in enumerate(polygons):
            for ring_index, ring in enumerate(polygon):
                points = [(e - ORIGIN[0], n - ORIGIN[1], terrain(e, n) + .08) for e, n in ring]
                obj = curve_object(f"FOOTPRINT_{feature['id']}_{index}_{ring_index}", points, .06, collections["REVIEW_OUTLINES"],
                                   match_mat if feature["id"] in matched else warning)
                obj["missing_matched_3d_candidate"] = feature["id"] not in matched
    line = prepared["pilot_route_epsg2326"]
    line_mat = material("PILOT_CENTRELINE_REFERENCE", (.03, .45, 1., 1.))
    points = []
    for a, b in zip(line, line[1:]):
        length = math.dist(a, b)
        for weight in np.linspace(0, 1, max(2, math.ceil(length / 2)), endpoint=False):
            e, n = np.asarray(a) * (1 - weight) + np.asarray(b) * weight
            points.append((e - ORIGIN[0], n - ORIGIN[1], terrain(e, n) + .12))
    e, n = line[-1]
    points.append((e - ORIGIN[0], n - ORIGIN[1], terrain(e, n) + .12))
    curve_object("PILOT_SOURCE_CENTRELINE", points, .08, collections["ROAD_REFERENCE"], line_mat)
    world = bpy.data.worlds.new("NEUTRAL_DAY_REVIEW")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.65, .72, .8, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .7
    sun_data = bpy.data.lights.new("DAY_SUN", "SUN")
    sun_data.energy = 2.5
    sun_data.angle = .12
    sun = bpy.data.objects.new("DAY_SUN", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (.55, -.35, -.4)
    camera_data = bpy.data.cameras.new("REVIEW_CAMERA")
    camera = bpy.data.objects.new("REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.clip_end = 3000
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1280, 800
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene["stage"] = "BUILDING SHAPE REVIEW - INCOMPLETE AUTHORING SCENE"
    scene["source_manifest_sha256"] = digest(prepared_path)
    text = bpy.data.texts.new("READ_ME_FIRST.txt")
    text.write("Kam Tin checkpoint 1-2 source building review. One unit is one metre.\n"
               "Clean and textured candidates occupy the same coordinates: enable one collection at a time.\n"
               "Orange outlines need a matched 3D source or manual authoring. Blue lines are source references.\n"
               "Native source heights retained. No flattening, road corridor clipping, facade generation or game export.\n"
               "Terrain orthophoto is layout reference. Missing buildings/occluded ground remain visible in imagery.\n"
               "Lands Department / CEDD / HKSAR Government data; road inventory: OpenStreetMap contributors.\n")
    render_records = []
    def aim(location, target, orthographic=False):
        camera.location = location
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera_data.type = "ORTHO" if orthographic else "PERSP"
        camera_data.ortho_scale = 580
        camera_data.lens = 32
    def render(name, variant, overlays):
        collections["CLEAN_BUILDING_CANDIDATES"].hide_render = variant != "clean"
        collections["TEXTURED_BUILDING_REFERENCES"].hide_render = variant != "textured_reference"
        collections["NATIVE_GENERIC_REFERENCE"].hide_render = variant != "textured_reference"
        collections["REVIEW_OUTLINES"].hide_render = not overlays
        collections["ROAD_REFERENCE"].hide_render = not overlays
        path = RENDERS / (name + ".png")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        render_records.append({"file": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "variant": variant,
                               "overlays": overlays, "camera_local_xyz": list(camera.location)})
    mid = np.asarray(line[len(line) // 2]) - ORIGIN
    aim((mid[0] + 300, mid[1] - 420, 370), (mid[0], mid[1], 7), True)
    render("01_clean_overview", "clean", True)
    render("02_textured_overview", "textured_reference", True)
    p = np.asarray(points[len(points) // 3])
    direction = np.asarray(points[min(len(points) - 1, len(points) // 3 + 10)]) - p
    direction[2] = 0
    direction /= np.linalg.norm(direction)
    aim(tuple(p + [-0., 0., 1.6]), tuple(p + direction * 35 + [0, 0, 1.6]))
    render("03_driver_forward", "textured_reference", False)
    p = np.asarray(points[2 * len(points) // 3])
    aim(tuple(p + [0, 0, 1.6]), tuple(p - direction * 35 + [0, 0, 1.6]))
    render("04_driver_reverse", "textured_reference", False)
    # Open in the clean authoring view. Raw photo geometry remains explicitly
    # opt-in for reference and must not look like an approved foreground build.
    collections["CLEAN_BUILDING_CANDIDATES"].hide_viewport = False
    collections["CLEAN_BUILDING_CANDIDATES"].hide_render = False
    collections["TEXTURED_BUILDING_REFERENCES"].hide_viewport = True
    collections["TEXTURED_BUILDING_REFERENCES"].hide_render = True
    collections["NATIVE_GENERIC_REFERENCE"].hide_viewport = True
    collections["NATIVE_GENERIC_REFERENCE"].hide_render = True
    collections["REVIEW_OUTLINES"].hide_render = False
    collections["ROAD_REFERENCE"].hide_render = False
    aim((mid[0] + 300, mid[1] - 420, 370), (mid[0], mid[1], 7), True)
    blend_path = ROOT / "blender/HK01_KamTin_BUILDING_REVIEW.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True)
    report = {"scope": "Separate building authoring/reference scene; not installed or game-tested",
              "scene": blend_path.relative_to(ROOT).as_posix(), "scene_sha256": digest(blend_path),
              "prepared_manifest_sha256": digest(prepared_path), "source_mesh_objects": len(source_models),
              "generic_reference_objects": generic_count,
              "generic_manifest_sha256": digest(generic_path) if generic_path.exists() else None,
              "default_view": "Clean building candidates and review outlines; raw photogrammetry hidden",
              "renders": render_records, "native_positions_preserved": True,
              "source_buildings_corridor_cut": False, "visual_review": "PENDING", "game_export": False}
    save(ROOT / "reports/building_review_scene.json", report)
    print("BUILDING_REVIEW_SCENE_COMPLETE", json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
