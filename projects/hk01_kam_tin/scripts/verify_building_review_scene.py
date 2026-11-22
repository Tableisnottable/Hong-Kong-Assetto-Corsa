"""Verify the saved authoring scene against its prepared source meshes in Blender."""
from pathlib import Path
import json
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collect_build_data import digest
from research_quality_sources import save


def main():
    output = ROOT / "gis/building_review"
    report = json.loads((ROOT / "reports/building_review_scene.json").read_text(encoding="utf-8"))
    scene_path = ROOT / report["scene"]
    if digest(scene_path) != report["scene_sha256"]:
        raise ValueError("Saved authoring scene changed after rendering")
    bpy.ops.wm.open_mainfile(filepath=str(scene_path))
    expected = {}
    prepared = json.loads((output / "prepared.json").read_text(encoding="utf-8"))
    if digest(output / "prepared.json") != report["prepared_manifest_sha256"]:
        raise ValueError("Prepared building inputs changed")
    for model in prepared["models"]:
        for index, part in enumerate(model["parts"]):
            expected[f"{model['variant']}_{model['model_id']}_{index}"] = output / part["mesh"]
    generic = json.loads((output / "generic_prepared.json").read_text(encoding="utf-8"))
    if digest(output / "generic_prepared.json") != report["generic_manifest_sha256"]:
        raise ValueError("Prepared native photogrammetry changed")
    for part in generic["models"]:
        expected[part["name"]] = output / part["mesh"]
    vertices_checked, triangles_checked = 0, 0
    for name, path in expected.items():
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise ValueError("Source mesh missing from scene: " + name)
        if not np.allclose(np.asarray(obj.matrix_world), np.eye(4), rtol=0, atol=1e-8):
            raise ValueError("Source building object has an extra transform")
        with np.load(path) as arrays:
            expected_vertices, expected_faces = arrays["vertices"], arrays["faces"]
        vertices = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
        obj.data.vertices.foreach_get("co", vertices)
        if not np.array_equal(vertices.reshape(-1, 3), expected_vertices):
            raise ValueError("Source positions flattened/shifted/changed in scene: " + name)
        obj.data.calc_loop_triangles()
        faces = np.empty(len(obj.data.loop_triangles) * 3, dtype=np.int32)
        obj.data.loop_triangles.foreach_get("vertices", faces)
        if not np.array_equal(faces.reshape(-1, 3), expected_faces):
            raise ValueError("Source triangle topology changed in scene: " + name)
        vertices_checked += len(expected_vertices)
        triangles_checked += len(expected_faces)
    for render in report["renders"]:
        if digest(ROOT / render["file"]) != render["sha256"]:
            raise ValueError("Render changed after scene build")
    if not bpy.data.collections["NATIVE_GENERIC_REFERENCE"].hide_viewport:
        raise ValueError("Raw photogrammetry should be hidden in the default authoring view")
    result = {"status": "PASS", "scope": "Saved authoring-scene source-position/topology verification only",
              "scene_sha256": report["scene_sha256"], "mesh_objects_checked": len(expected),
              "vertices_checked": vertices_checked, "triangles_checked": triangles_checked,
              "renders_hash_verified": len(report["renders"]), "native_positions_preserved": True,
              "default_raw_photogrammetry_hidden": True,
              "limits": "Not a road/collision/KN5 check, game test, or approval of source mesh appearance"}
    save(ROOT / "reports/building_review_scene_verification.json", result)
    print("BUILDING_REVIEW_VERIFIED", json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
