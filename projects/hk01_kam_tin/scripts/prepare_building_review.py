"""Prepare intact official building candidates for the checkpoint 1-2 review.

Accepts untextured vertex-colour glTF and textured glTF. Makes a separate local
authoring input set, without changing collision, sources or installed tracks.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import urllib.parse
import zipfile

import numpy as np
from shapely.geometry import LineString, MultiPoint, Point, box, shape
from shapely.ops import substring

from collect_build_data import ROOT, digest
from prepare_csdi_scenery import accessor, node_matrix
from research_quality_sources import save

ORIGIN = np.array([826000., 833000., 0.])
OUTPUT = ROOT / "gis/building_review"


def local_resource(parent, uri):
    uri = urllib.parse.unquote(uri)
    if urllib.parse.urlsplit(uri).scheme or "\\" in uri:
        raise ValueError("Only relative local glTF dependencies are supported")
    path = (parent / uri).resolve()
    if not path.is_relative_to(parent.resolve()):
        raise ValueError("glTF dependency escapes its source model folder")
    return path


def model_primitives(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    buffers = [local_resource(path.parent, b["uri"]).read_bytes() for b in document["buffers"]]
    active = set()
    def visit(index, parent):
        if index in active:
            raise ValueError("Cyclic glTF node hierarchy")
        active.add(index)
        node = document["nodes"][index]
        matrix = parent @ node_matrix(node)
        if "mesh" in node:
            for primitive in document["meshes"][node["mesh"]]["primitives"]:
                if primitive.get("mode", 4) != 4:
                    raise ValueError("Expected triangle building geometry")
                positions = accessor(document, buffers, primitive["attributes"]["POSITION"]).astype(np.float64)
                world = positions @ matrix[:3, :3].T + matrix[:3, 3]
                vertices = world[:, [0, 2, 1]] * [1, -1, 1] - ORIGIN
                indices = (accessor(document, buffers, primitive["indices"]).ravel() if "indices" in primitive
                           else np.arange(len(vertices)))
                if len(indices) % 3 or (len(indices) and (indices.min() < 0 or indices.max() >= len(vertices))):
                    raise ValueError("Invalid building triangle indices")
                faces = indices.reshape(-1, 3).astype(np.int32)
                if np.linalg.det(matrix[:3, :3]) < 0:
                    faces = faces[:, [0, 2, 1]]
                attributes = primitive["attributes"]
                uv = accessor(document, buffers, attributes["TEXCOORD_0"]) if "TEXCOORD_0" in attributes else None
                if uv is not None:
                    uv[:, 1] = 1 - uv[:, 1]
                colors = accessor(document, buffers, attributes["COLOR_0"]) if "COLOR_0" in attributes else None
                material = document.get("materials", [{}])[primitive.get("material", 0)]
                pbr = material.get("pbrMetallicRoughness", {})
                image = None
                texture = pbr.get("baseColorTexture")
                if texture:
                    entry = document["images"][document["textures"][texture["index"]]["source"]]
                    image = local_resource(path.parent, entry["uri"])
                yield {"vertices": vertices, "faces": faces, "uv": uv, "colors": colors,
                       "image": image, "color": pbr.get("baseColorFactor", [.65, .65, .65, 1.])}
        for child in node.get("children", []):
            yield from visit(child, matrix)
        active.remove(index)
    for index in document["scenes"][document.get("scene", 0)]["nodes"]:
        yield from visit(index, np.eye(4))


def pilot_line():
    source = json.loads((ROOT / "driving_test/source/test_loop_source.json").read_text(encoding="utf-8"))
    checkpoints = json.loads((ROOT / "driving_test/source/checkpoints.json").read_text(encoding="utf-8"))
    line = LineString(source["xy"])
    points = [Point(c["local_xyz_m"][0] + ORIGIN[0], c["local_xyz_m"][1] + ORIGIN[1]) for c in checkpoints[:2]]
    distances = [line.project(p) for p in points]
    section = substring(line, *distances)
    if not 400 < section.length < 470:
        raise ValueError("Checkpoint source-line selection does not match the approved pilot")
    return section


def topology(vertices, faces):
    if not np.isfinite(vertices).all():
        raise ValueError("Non-finite building positions")
    lengths = np.linalg.norm(np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]],
                                      vertices[faces[:, 2]] - vertices[faces[:, 0]]), axis=1)
    valid = lengths > 1e-7
    faces = faces[valid]
    _, welded = np.unique(np.round(vertices, 3), axis=0, return_inverse=True)
    wf = welded[faces]
    edge_counts = Counter(tuple(sorted((int(a), int(b)))) for f in wf for a, b in zip(f, np.roll(f, -1)) if a != b)
    extents = np.ptp(vertices, axis=0)
    return faces, {"degenerate_triangles_removed": int((~valid).sum()),
                   "boundary_edges_at_1mm_weld": sum(count == 1 for count in edge_counts.values()),
                   "nonmanifold_edges_at_1mm_weld": sum(count > 2 for count in edge_counts.values()),
                   "extent_m": extents.tolist(), "flat_geometry": bool(extents[2] < .5)}


def extract_selected(archive_path, selected, destination, category="BUILDING"):
    """Extract only selected model folders; never overwrite author edits."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            parts = Path(info.filename.replace("\\", "/")).parts
            if len(parts) < 3 or parts[0] != category or parts[1] not in selected or info.is_dir():
                continue
            target = (destination / Path(*parts)).resolve()
            if not target.is_relative_to(destination.resolve()) or info.file_size > 768 * 1024**2:
                raise ValueError("Unexpected selected building dependency")
            data = archive.read(info)  # ZipFile checks member CRC while reading.
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError("Preserving edited selected model: " + target.name)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "meshes").mkdir(exist_ok=True)
    line = pilot_line()
    footprints = json.loads((ROOT / "gis/high_quality_full_loop/LandsD_building_footprints_full_loop_grid.json").read_text(encoding="utf-8"))["features"]
    nearby = [f for f in footprints if shape(f["geometry"]).distance(line) <= 60]
    by_ref = {}
    for feature in nearby:
        by_ref.setdefault(str(feature["properties"].get("GeoRefNo")), []).append(feature)
    selected, candidates, checked_archives = set(), [], []
    models = sorted((ROOT / "source/map_build_full_loop/extracted").glob("nontextured_models_*/BUILDING/*/*.gltf"))
    model_paths = []
    seen = set()
    for path in models:
        match = re.match(r"B(\d{10})", path.stem)
        if not match or match[1] not in by_ref or path.stem in seen:
            continue
        seen.add(path.stem)
        selected.add(path.stem)
        model_paths.append(("clean", path, by_ref[match[1]]))
    manifest = json.loads((ROOT / "source/map_build_full_loop/local_manifest.json").read_text(encoding="utf-8"))
    for record in manifest["files"]:
        if record["role"] != "individualised_models":
            continue
        archive_path = Path(record["local_path"])
        with zipfile.ZipFile(archive_path) as archive:
            names = []
            for name in archive.namelist():
                match = re.match(r"B(\d{10})", Path(name).stem)
                if name.startswith("BUILDING/") and name.endswith(".gltf") and match and match[1] in by_ref:
                    names.append(name)
        if not names:
            continue
        if digest(archive_path) != record["sha256"]:
            raise ValueError("Individualised source archive changed")
        destination = ROOT / "source/building_review_selected" / archive_path.stem
        extract_selected(archive_path, {Path(name).stem for name in names}, destination)
        checked_archives.append({"name": record["name"], "sha256": record["sha256"]})
        for name in names:
            path = destination / name
            match = re.match(r"B(\d{10})", path.stem)
            model_paths.append(("textured_reference", path, by_ref[match[1]]))
    used_keys = set()
    for variant, path, matches in model_paths:
        key = (variant, path.stem)
        if key in used_keys:
            continue
        used_keys.add(key)
        parts = list(model_primitives(path))
        all_vertices = np.concatenate([p["vertices"] for p in parts])
        footprint = MultiPoint(all_vertices[:, :2] + ORIGIN[:2]).convex_hull
        matching = max(matches, key=lambda f: footprint.intersection(shape(f["geometry"])).area)
        outline = shape(matching["geometry"])
        intersection = footprint.intersection(outline).area
        union = footprint.union(outline).area
        overlap = intersection / union if union else 0
        distance = footprint.distance(line)
        if distance > 65:
            continue
        assets = []
        for index, part in enumerate(parts):
            faces, checks = topology(part["vertices"], part["faces"])
            if not len(faces):
                continue
            filename = f"{variant}_{path.stem}_{index}.npz"
            arrays = {"vertices": part["vertices"].astype(np.float32), "faces": faces}
            for name in ("uv", "colors"):
                if part[name] is not None:
                    arrays[name] = part[name].astype(np.float32)
            np.savez_compressed(OUTPUT / "meshes" / filename, **arrays)
            assets.append({"mesh": "meshes/" + filename, "checks": checks, "triangles": len(faces),
                           "texture": part["image"].relative_to(ROOT).as_posix() if part["image"] and part["image"].exists() else None,
                           "missing_source_texture": bool(part["image"] and not part["image"].exists()),
                           "base_color": part["color"], "has_vertex_colors": part["colors"] is not None})
        props = matching["properties"]
        extent = np.ptp(all_vertices, axis=0)
        flags = []
        if overlap < .5:
            flags.append("footprint_overlap_below_50_percent")
        if extent[2] < .5:
            flags.append("flat_geometry")
        if props["HEIGHT_M"] and abs(float(extent[2]) - props["HEIGHT_M"]) > 2:
            flags.append("attribute_height_difference_over_2m")
        if any(a["missing_source_texture"] for a in assets):
            flags.append("missing_source_texture")
        candidates.append({"model_id": path.stem, "variant": variant,
                           "source_file": path.relative_to(ROOT).as_posix(), "source_gltf_sha256": digest(path),
                           "building_object_id": matching["id"], "georef_no": props["GeoRefNo"],
                           "distance_to_pilot_m": distance, "footprint_hull_iou": overlap,
                           "native_base_m": float(all_vertices[:, 2].min()), "native_top_m": float(all_vertices[:, 2].max()),
                           "native_extent_m": extent.tolist(), "attribute_height_m": props["HEIGHT_M"],
                           "flags": flags, "parts": assets})
    prepared = {"scope": "Checkpoint 1-2 intact building geometry comparison; authoring reference only",
                "origin_epsg2326": ORIGIN[:2].tolist(), "pilot_route_epsg2326": list(line.coords),
                "nearby_building_footprints": nearby, "models": candidates,
                "limits": ["No source building flattened, shifted vertically, corridor-cut or installed.",
                           "Convex-hull footprint overlap is a screening measure, not an exact silhouette match.",
                           "Native source geometry/colour/texture is retained for inspection; facades are not authored or approved."]}
    save(OUTPUT / "prepared.json", prepared)
    report = {k: v for k, v in prepared.items() if k not in ("models", "nearby_building_footprints")}
    report.update(nearby_footprints=len(nearby), candidate_models=len(candidates),
                  variants=dict(Counter(c["variant"] for c in candidates)),
                  flagged_models=sum(bool(c["flags"]) for c in candidates),
                  matched_footprint_ids=len({c["building_object_id"] for c in candidates}),
                  source_archives_checked=checked_archives, prepared_manifest_sha256=digest(OUTPUT / "prepared.json"),
                  output_folder="gis/building_review/", triangle_count=sum(a["triangles"] for c in candidates for a in c["parts"]))
    save(ROOT / "reports/building_candidate_review.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
