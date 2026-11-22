"""Retain native GENERIC photogrammetry in the pilot authoring review.

GENERIC can contain real structures. Never flatten the category onto terrain.
These meshes are a clipped source reference; they are not finished buildings.
"""
from collections import Counter
import json
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image

from collect_build_data import ROOT, digest
from prepare_building_review import ORIGIN, OUTPUT, extract_selected, local_resource
from prepare_csdi_scenery import accessor, node_matrix
from research_quality_sources import save


def clipped_primitives(path, bounds):
    document = json.loads(path.read_text(encoding="utf-8"))
    blobs = [local_resource(path.parent, b["uri"]).read_bytes() for b in document["buffers"]]
    west, south, east, north = bounds
    def visit(index, parent):
        node = document["nodes"][index]
        matrix = parent @ node_matrix(node)
        world_cache = {}
        if "mesh" in node:
            for number, primitive in enumerate(document["meshes"][node["mesh"]]["primitives"]):
                if primitive.get("mode", 4) != 4:
                    raise ValueError("Expected source triangle primitive")
                position = primitive["attributes"]["POSITION"]
                if position not in world_cache:
                    v = accessor(document, blobs, position).astype(np.float64)
                    v = v @ matrix[:3, :3].T + matrix[:3, 3]
                    world_cache[position] = v[:, [0, 2, 1]] * [1, -1, 1] - ORIGIN
                vertices = world_cache[position]
                faces = accessor(document, blobs, primitive["indices"]).reshape(-1, 3).astype(np.int32)
                p = vertices[faces, :2] + ORIGIN[:2]
                # Context cut only, keeping whole triangles. No corridor cut and
                # no height projection. Source categories retain their identity.
                keep = (p[:, :, 0].max(axis=1) >= west) & (p[:, :, 0].min(axis=1) <= east) & (
                    p[:, :, 1].max(axis=1) >= south) & (p[:, :, 1].min(axis=1) <= north)
                faces = faces[keep]
                if not len(faces):
                    continue
                used, inverse = np.unique(faces, return_inverse=True)
                result = {"vertices": vertices[used].astype(np.float32), "faces": inverse.reshape(-1, 3).astype(np.int32)}
                if np.linalg.det(matrix[:3, :3]) < 0:
                    result["faces"] = result["faces"][:, [0, 2, 1]]
                if "TEXCOORD_0" in primitive["attributes"]:
                    uv = accessor(document, blobs, primitive["attributes"]["TEXCOORD_0"])[used]
                    uv[:, 1] = 1 - uv[:, 1]
                    result["uv"] = uv.astype(np.float32)
                material = document.get("materials", [{}])[primitive.get("material", 0)]
                pbr = material.get("pbrMetallicRoughness", {})
                ref = pbr.get("baseColorTexture")
                texture = None
                if ref:
                    image = document["images"][document["textures"][ref["index"]]["source"]]
                    texture = local_resource(path.parent, image["uri"])
                yield number, result, texture, pbr.get("baseColorFactor", [.65, .65, .65, 1])
        for child in node.get("children", []):
            yield from visit(child, matrix)
    for index in document["scenes"][document.get("scene", 0)]["nodes"]:
        yield from visit(index, np.eye(4))


def main():
    raw = ROOT / "source/map_build_full_loop"
    manifest = json.loads((raw / "local_manifest.json").read_text(encoding="utf-8"))
    bounds = json.loads((ROOT / "reports/map_data_acquisition.json").read_text(encoding="utf-8"))["bounds_epsg2326"]
    models, checked = [], []
    (OUTPUT / "textures").mkdir(exist_ok=True)
    for record in manifest["files"]:
        if record["role"] != "individualised_models" or not any(sheet in record["name"] for sheet in ("6-NE-12D", "6-NE-13C", "6-NE-17B", "6-NE-18A")):
            continue
        path = Path(record["local_path"])
        if digest(path) != record["sha256"]:
            raise ValueError("Source photogrammetry archive changed")
        with zipfile.ZipFile(path) as archive:
            names = [n for n in archive.namelist() if n.startswith("GENERIC/") and n.endswith(".gltf")]
        destination = ROOT / "source/building_review_selected" / path.stem
        extract_selected(path, {Path(name).parts[1] for name in names}, destination, category="GENERIC")
        checked.append({"name": record["name"], "sha256": record["sha256"]})
        for name in names:
            source = destination / name
            for index, arrays, texture, color in clipped_primitives(source, bounds):
                key = f"generic_{record['name'].removesuffix('.zip')}_{source.stem}_{index}"
                file = OUTPUT / "meshes" / (key + ".npz")
                # Preserve non-finite source UVs as a rejection, not a silent repair.
                if "uv" in arrays and not np.isfinite(arrays["uv"]).all():
                    raise ValueError("Non-finite generic source UVs require explicit repair")
                if not np.isfinite(arrays["vertices"]).all():
                    raise ValueError("Non-finite generic source positions")
                np.savez_compressed(file, **arrays)
                image_out = None
                if texture and texture.exists():
                    image_out = OUTPUT / "textures" / (key + ".jpg")
                    with Image.open(texture) as image:
                        image = image.convert("RGB")
                        image.thumbnail((2048, 2048))
                        image.save(image_out, quality=95)
                models.append({"name": key, "mesh": file.relative_to(OUTPUT).as_posix(),
                               "source_file": source.relative_to(ROOT).as_posix(), "source_category": "GENERIC",
                               "triangles": len(arrays["faces"]), "base_color": color,
                               "texture": image_out.relative_to(ROOT).as_posix() if image_out else None,
                               "native_heights_preserved": True})
            print("Generic review:", source.stem, flush=True)
    save(OUTPUT / "generic_prepared.json", {"models": models, "bounds_epsg2326": bounds,
         "limits": "Context-window triangle selection only; may include ground, vegetation and incomplete structures. Not an individual building replacement."})
    report = {"scope": "Native GENERIC source geometry retained for authoring review", "source_archives_checked": checked,
              "mesh_parts": len(models), "triangles": sum(m["triangles"] for m in models),
              "manifest_sha256": digest(OUTPUT / "generic_prepared.json"), "flattened_vertices": 0,
              "road_corridor_cut": False, "game_export": False,
              "limits": ["Source ground, vegetation, rough facades and boundary cuts remain; no production-quality claim.",
                         "2K texture caps are review previews; original source textures remain untouched."]}
    save(ROOT / "reports/generic_geometry_review.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
