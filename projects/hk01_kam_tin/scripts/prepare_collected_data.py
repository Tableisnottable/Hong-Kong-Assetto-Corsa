"""Verify and unpack collected pilot sources; make an unmodified LiDAR crop.

Requires NumPy and Pillow, as used by the existing project. Does not build,
install, or launch an Assetto Corsa track. All generated inputs stay ignored.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile
import zlib

import numpy as np
from PIL import Image
from shapely.geometry import box, LineString, MultiLineString, MultiPolygon, Point, Polygon, mapping
from shapely.validation import make_valid

from collect_build_data import ROOT, digest, inspect_archive, selection
from research_quality_sources import save


def unpack(path, folder, expected_hash):
    if digest(path) != expected_hash:
        raise ValueError("Archive changed after acquisition: " + path.name)
    inspect_archive(path)
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            target = (folder / member.filename.replace("\\", "/")).resolve()
            if not target.is_relative_to(folder.resolve()):
                raise ValueError("Unsafe extraction path")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if target.exists():
                crc = 0
                with target.open("rb") as stream:
                    while chunk := stream.read(1024**2):
                        crc = zlib.crc32(chunk, crc)
                if target.stat().st_size != member.file_size or crc != member.CRC:
                    raise ValueError("Preserving modified extracted source: " + target.name)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("xb") as dest:
                shutil.copyfileobj(source, dest, 1024**2)
    return folder


def gml_counts(folder):
    counts = {}
    for path in folder.rglob("*.gml"):
        for _, element in ET.iterparse(path, events=("end",)):
            if element.tag.split("}")[-1] in {"featureMember", "member"} and len(element):
                kind = element[0].tag.split("}")[-1]
                counts[kind] = counts.get(kind, 0) + 1
                element.clear()
    return counts


def orthophoto_summary(raw, catalog, bounds):
    row_path = raw / "index/tdop_features.json"
    features = json.loads(row_path.read_text(encoding="utf-8"))["features"]
    feature = next(f for f in features if f["attributes"].get("SHEETNO") == "T6-NE-C")
    prepared = next(i for i in catalog if i["role"] == "tdop")
    folder = ROOT / prepared["folder"]
    world = next(folder.rglob("*.tfw"), None)
    image_path = next((p for p in folder.rglob("*.tif") if p.is_file()), None)
    if world is None or image_path is None:
        raise FileNotFoundError("Orthophoto TIFF and world file are both required")
    a, d, b, e, x_center, y_center = [float(v) for v in world.read_text().split()]
    if d or b or a <= 0 or e >= 0:
        raise ValueError("Unexpected rotated or south-up orthophoto world file")
    image_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None  # Header only; do not decode the full raster.
    try:
        with Image.open(image_path) as image:
            width, height, mode = image.width, image.height, image.mode
    finally:
        Image.MAX_IMAGE_PIXELS = image_limit
    west, south, east, north = bounds
    extent = [x_center - a / 2, y_center + e * (height - .5),
              x_center + a * (width - .5), y_center - e / 2]
    if not (extent[0] <= west and extent[1] <= south and extent[2] >= east and extent[3] >= north):
        raise ValueError("Orthophoto does not cover the complete pilot envelope")
    return {"dataset_id": "landsd_rcd_1701762716904_4826", "sheet": "T6-NE-C",
            "photograph_date": feature["attributes"].get("DATE_OF_PHOTOGRAPH"),
            "source_image": image_path.relative_to(ROOT).as_posix(),
            "source_dimensions_pixels": [width, height], "source_mode": mode,
            "ground_sample_distance_m": a,
            "source_pixel_centres_epsg2326_first": [x_center, y_center],
            "source_extent_edges_epsg2326": extent, "pilot_fully_covered": True,
            "georeferencing": "Companion TIFF world file; horizontal CRS from LandsD TDOP metadata"}


def terrain_crop(folders, bounds, output, prefix="pilot"):
    west, south, east, north = bounds
    cell = 0.5
    result = np.full((round((north - south) / cell), round((east - west) / cell)), np.nan, dtype=np.float32)
    grids = []
    for folder in folders:
        for path in folder.rglob("*.tif"):
            with Image.open(path) as image:
                scale = image.tag_v2.get(33550)
                tie = image.tag_v2.get(33922)
                keys = image.tag_v2.get(34735)
                raster_type = next((keys[i + 3] for i in range(4, len(keys), 4) if keys[i] == 1025), None)
                if raster_type != 1 or tuple(scale[:2]) != (cell, cell) or tuple(tie[:2]) != (0.0, 0.0):
                    raise ValueError("Expected an unrotated 0.5 m PixelIsArea DTM")
                x0, y0 = tie[3:5]
                left = max(0, round((west - x0) / cell))
                top = max(0, round((y0 - north) / cell))
                right = min(image.width, round((east - x0) / cell))
                bottom = min(image.height, round((y0 - south) / cell))
                if left >= right or top >= bottom:
                    continue
                values = np.asarray(image.crop((left, top, right, bottom)), dtype=np.float32).copy()
                nodata = image.tag_v2.get(42113)
                if nodata is not None:
                    values[values == float(nodata)] = np.nan
                col = round((x0 + left * cell - west) / cell)
                row = round((north - (y0 - top * cell)) / cell)
                dest = result[row:row + values.shape[0], col:col + values.shape[1]]
                both = np.isfinite(dest) & np.isfinite(values)
                if both.any() and not np.allclose(dest[both], values[both], atol=0.01):
                    raise ValueError("Conflicting overlapping DTM samples")
                np.copyto(dest, values, where=np.isfinite(values))
                grids.append({"file": path.name, "width": image.width, "height": image.height,
                              "pixel_size_m": cell, "upper_left_edge_epsg2326": [x0, y0]})
    missing = int(np.isnan(result).sum())
    if missing:
        raise ValueError(f"Pilot terrain has {missing} uncovered pixels")
    output.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_dtm_05m.npz"
    np.savez_compressed(output / filename, z=result, cell_m=cell,
                        west_edge=west, north_edge=north,
                        x_first_center=west + cell / 2, y_first_center=north - cell / 2,
                        horizontal_epsg=2326, origin_epsg2326=[826000, 833000])
    return {"file": (output / filename).relative_to(ROOT).as_posix(), "shape": list(result.shape),
            "pixel_size_m": cell, "nodata_pixels": missing,
            "min_native_height_m": float(result.min()), "max_native_height_m": float(result.max()),
            "grids": grids, "processing": "Pixel-aligned crop and mosaic; no smoothing or vertical offset",
            "vertical_reference": "Native LiDAR heights; confirm datum in source documentation before road profile authoring"}


def crop_orthophoto(raw, catalog, bounds, output):
    source_record = json.loads((raw / "index/tdop_features.json").read_text(encoding="utf-8"))
    tile = next(f for f in source_record["features"] if f["attributes"].get("SHEETNO") == "T6-NE-C")
    folder = ROOT / next(i["folder"] for i in catalog if i["role"] == "tdop")
    image_path = next(folder.rglob("*.tif"))
    world_file = next(folder.rglob("*.tfw"))
    a, d, b, e, x0, y0 = map(float, world_file.read_text(encoding="ascii").split())
    if (d, b) != (0.0, 0.0) or a <= 0 or e >= 0:
        raise ValueError("Unsupported orthophoto world-file orientation")
    west, south, east, north = bounds
    cell_x, cell_y = a, -e
    tile_west, tile_north = x0 - cell_x / 2, y0 + cell_y / 2
    left = round((west - tile_west) / cell_x)
    right = round((east - tile_west) / cell_x)
    top = round((tile_north - north) / cell_y)
    bottom = round((tile_north - south) / cell_y)
    if any(abs(v - round(v)) > 1e-7 for v in ((west - tile_west) / cell_x,
                                               (east - tile_west) / cell_x,
                                               (tile_north - north) / cell_y,
                                               (tile_north - south) / cell_y)):
        raise ValueError("Pilot envelope is not aligned with orthophoto pixels")
    max_pixels = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(image_path) as image:
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError("Pilot crop exceeds the orthophoto tile")
            crop = image.crop((left, top, right, bottom)).convert("RGB")
            if crop.size != (round((east - west) / cell_x), round((north - south) / cell_y)):
                raise ValueError("Orthophoto crop dimensions do not match the pilot bounds")
            path = output / "pilot_orthophoto.jpg"
            crop.save(path, format="JPEG", quality=95, subsampling=0, optimize=True)
    finally:
        Image.MAX_IMAGE_PIXELS = max_pixels
    first_center_e, first_center_n = x0 + left * cell_x, y0 - top * cell_y
    path.with_suffix(".jgw").write_text(
        f"{cell_x:.9f}\n0.000000000\n0.000000000\n{-cell_y:.9f}\n"
        f"{first_center_e:.9f}\n{first_center_n:.9f}\n", encoding="ascii")
    path.with_suffix(".crs.txt").write_text("EPSG:2326\n", encoding="ascii")
    return {"dataset_id": "landsd_rcd_1701762716904_4826", "sheet": "T6-NE-C",
            "photograph_date": tile["attributes"].get("DATE_OF_PHOTOGRAPH"),
            "source_ground_sample_distance_m": cell_x,
            "crop_file": path.relative_to(ROOT).as_posix(),
            "world_file": path.with_suffix(".jgw").relative_to(ROOT).as_posix(),
            "crs_file": path.with_suffix(".crs.txt").relative_to(ROOT).as_posix(),
            "dimensions_pixels": list(crop.size), "bounds_epsg2326": bounds,
            "pixel_centres_epsg2326_first": [first_center_e, first_center_n],
            "resampling": "None; lossless pixel-window crop then JPEG quality 95 for practical viewing",
            "alignment": "PASS"}


def scalar_properties(feature, geometry_node):
    props = {}
    for child in feature:
        if child is geometry_node:
            continue
        name = child.tag.split("}")[-1].upper()
        if len(child) == 0 and child.text and child.text.strip():
            props[name] = child.text.strip()
    return props


def geometry_sequences(geometry_node):
    nodes = [node for node in geometry_node.iter()
             if node.tag.split("}")[-1] in {"posList", "pos"}]
    sequences = []
    for node in nodes:
        values = [float(v) for v in node.text.split()]
        dimension = int(node.attrib.get("srsDimension", node.attrib.get("dimension", 0)) or 0)
        if not dimension:
            # GML data sometimes omit srsDimension on the coordinate element.
            # EPSG:2326 positions are around 800,000 m; a third ordinate is a
            # comparatively small elevation. This disambiguates 2D/3D lists.
            triple_heights = (len(values) >= 3 and len(values) % 3 == 0
                              and all(abs(values[i + 2]) < 10000
                                      and abs(values[i]) > 10000 and abs(values[i + 1]) > 10000
                                      for i in range(0, len(values), 3)))
            dimension = 3 if len(values) % 3 == 0 and (len(values) % 2 != 0 or triple_heights) else 2
        if len(values) % dimension:
            raise ValueError("Malformed GML coordinate list")
        sequences.append([values[i:i + dimension] for i in range(0, len(values), dimension)])
    return sequences


def find_gml_geometry(feature, wanted):
    for node in feature.iter():
        if node.tag.split("}")[-1] in wanted:
            return node
    return None


def axis_order_check(raw, folders, bounds):
    tile_index = json.loads((raw / "index/ib1000_features.json").read_text(encoding="utf-8"))["features"]
    extents = {}
    for entry in tile_index:
        name = entry["attributes"]["SHEETNO"]
        points = entry["geometry"]["rings"][0]
        extents[name] = (min(p[0] for p in points) - 2, min(p[1] for p in points) - 2,
                         max(p[0] for p in points) + 2, max(p[1] for p in points) + 2)
    in_en, in_ne = 0, 0
    for folder in folders:
        sheet = folder.name.removeprefix("ib1000_")
        extent = extents[sheet]
        for path in folder.rglob("StreetCentreLines.gml"):
            sampled = 0
            for _, element in ET.iterparse(path, events=("end",)):
                if element.tag.split("}")[-1] != "featureMember":
                    continue
                geom = find_gml_geometry(element, {"LineString", "Curve"})
                if geom is not None:
                    seqs = geometry_sequences(geom)
                    if seqs and seqs[0]:
                        first = seqs[0][0]
                        if len(first) >= 2:
                            n, e = first[0], first[1]
                            in_ne += int(extent[0] <= e <= extent[2] and extent[1] <= n <= extent[3])
                            in_en += int(extent[0] <= n <= extent[2] and extent[1] <= e <= extent[3])
                            sampled += 1
                element.clear()
                if sampled >= 100:
                    break
    if not in_ne or in_ne < in_en * 20:
        raise ValueError("iB1000 coordinate axis order failed tile-boundary cross-check")
    return {"source_axis_order": "northing,easting,height", "output_axis_order": "easting,northing",
            "tile_boundary_samples": {"northing_easting_matches": in_ne,
                                       "easting_northing_matches": in_en},
            "check": "PASS: GML positions cross-checked against official EPSG:2326 tile extents"}


def clip_ib1000(raw, folders, bounds, output, prefix="pilot"):
    clip = box(bounds[0], bounds[1], bounds[2], bounds[3])
    layers = {
        "StreetCentreLines": {"LineString", "Curve"},
        "CartoTransLine": {"LineString", "Curve"},
        "SpotHeight": {"Point"},
    }
    if prefix != "pilot":
        layers.update(UtilityPoint={"Point"}, CartoPedLine={"LineString", "Curve"},
                      UtilityLine={"LineString", "Curve"})
    summary = {}
    for layer, geometry_types in layers.items():
        rows, codes, no_display = [], {}, 0
        seen = set()
        for folder in folders:
            sheet = folder.name.removeprefix("ib1000_")
            for path in folder.rglob(layer + ".gml"):
                for _, member in ET.iterparse(path, events=("end",)):
                    if member.tag.split("}")[-1] != "featureMember" or not len(member):
                        continue
                    feature = member[0]
                    geometry_node = find_gml_geometry(feature, geometry_types)
                    if geometry_node is None:
                        member.clear()
                        continue
                    props = scalar_properties(feature, geometry_node)
                    source_id = props.get(layer.upper() + "ID") or feature.attrib.get("{http://www.opengis.net/gml}id")
                    if source_id in seen:
                        member.clear()
                        continue
                    seen.add(source_id)
                    sequences = geometry_sequences(geometry_node)
                    geom_kind = geometry_node.tag.split("}")[-1]
                    if "Point" in geometry_types:
                        if not sequences or not sequences[0] or len(sequences[0][0]) < 2:
                            member.clear()
                            continue
                        n, e = sequences[0][0][:2]
                        geometry = Point(e, n)
                    else:
                        parts = []
                        for sequence in sequences:
                            coords = [(v[1], v[0]) for v in sequence if len(v) >= 2]
                            if len(coords) >= 2:
                                parts.append(LineString(coords))
                        if not parts:
                            member.clear()
                            continue
                        geometry = parts[0] if len(parts) == 1 else MultiLineString(parts)
                    clipped = geometry.intersection(clip)
                    if not clipped.is_empty:
                        if props.get("DISPLAYSTATUS") not in (None, "0", "1"):
                            no_display += 1
                        code_name = "STREETTYPE" if layer == "StreetCentreLines" else (
                            "TRANSPORTATIONLINETYPE" if layer == "CartoTransLine" else "FEATURETYPE")
                        code = props.get(code_name, "UNKNOWN")
                        codes[code] = codes.get(code, 0) + 1
                        rows.append({"type": "Feature", "id": source_id,
                                     "properties": dict(props, SOURCE_SHEET=sheet),
                                     "geometry": mapping(clipped)})
                    member.clear()
        name = f"iB1000_{layer}_{prefix}_grid.json"
        payload = {"type": "FeatureCollection", "coordinate_system": "EPSG:2326",
                   "coordinate_axis_order": "easting,northing", "source_axis_order": "northing,easting,height",
                   "height_note": "GML third ordinates in line/point geometry are not promoted to road/deck height; use coded attributes and survey review.",
                   "source_tiles": [p.name.removeprefix("ib1000_") for p in folders],
                   "features": rows}
        (output / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        summary[layer] = {"file": (output / name).relative_to(ROOT).as_posix(),
                          "pilot_features" if prefix == "pilot" else "envelope_features": len(rows),
                          "clipped_counts_by_code": codes, "records_with_other_display_status": no_display}
    return summary


def clip_buildings(raw, bounds, output, prefix="pilot"):
    source = json.loads((raw / "index/buildings_features.json").read_text(encoding="utf-8"))["features"]
    clip = box(bounds[0], bounds[1], bounds[2], bounds[3])
    rows, unknown = [], 0
    for item in source:
        rings = item["geometry"].get("rings", [])
        if not rings:
            continue
        shells, holes = [], []
        for ring in rings:
            area = sum(ring[i][0] * ring[(i + 1) % len(ring)][1]
                       - ring[(i + 1) % len(ring)][0] * ring[i][1]
                       for i in range(len(ring))) / 2
            (shells if area < 0 else holes).append(ring)
        parts = [(shell, []) for shell in shells]
        for hole in holes:
            hole_poly = Polygon(hole)
            owner = next((i for i, (shell, _) in enumerate(parts)
                          if Polygon(shell).covers(hole_poly.representative_point())), None)
            if owner is None:
                raise ValueError("Esri building hole does not fall inside an outer footprint ring")
            parts[owner][1].append(hole)
        polygons = [Polygon(shell, part_holes) for shell, part_holes in parts]
        geom = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
        if not geom.is_valid:
            geom = make_valid(geom)
        geom = geom.intersection(clip)
        if geom.is_empty:
            continue
        attrs = item["attributes"]
        base, top = attrs.get("BaseHeight"), attrs.get("TopHeight")
        valid = isinstance(base, (int, float)) and isinstance(top, (int, float)) and top > base
        unknown += not valid
        props = {key: attrs.get(key) for key in ("OBJECTID", "GeoRefNo", "BuildingID", "BuildingCSUID",
                                                  "BuildingBlockType", "BuildingNameEN", "BuildingNameTC",
                                                  "Status", "BaseHeight", "TopHeight", "Storeys")}
        props["HEIGHT_M"] = top - base if valid else None
        props["HEIGHT_REVIEW_REQUIRED"] = not valid
        rows.append({"type": "Feature", "id": str(attrs.get("OBJECTID")),
                     "properties": props, "geometry": mapping(geom)})
    name = f"LandsD_building_footprints_{prefix}_grid.json"
    payload = {"type": "FeatureCollection", "coordinate_system": "EPSG:2326",
               "coordinate_axis_order": "easting,northing", "features": rows}
    (output / name).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"file": (output / name).relative_to(ROOT).as_posix(), "clipped_footprints": len(rows),
            "known_base_top_heights": len(rows) - unknown, "height_review_required": unknown}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("pilot", "full-loop"), default="pilot")
    parser.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    bounds, folder_name, _ = selection(args.scope)
    raw = (args.source_dir or ROOT / "source" / folder_name).resolve()
    if not raw.is_relative_to((ROOT / "source").resolve()):
        parser.error("Source directory must be inside the project's ignored source/")
    manifest = json.loads((raw / "local_manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "PASS" or manifest["bounds_epsg2326"] != bounds:
        raise ValueError("Complete acquisition for the selected bounds is required before preparation")
    prefix = "pilot" if args.scope == "pilot" else "full_loop"
    catalog, terrain = [], []
    for record in manifest["files"]:
        if record["status"] != "PASS":
            continue
        path = Path(record["local_path"])
        if path.suffix.lower() != ".zip" or record["role"] in {"hk_foundation", "individualised_models"}:
            continue
        folder = unpack(path, raw / "extracted" / path.stem, record["sha256"])
        item = {"role": record["role"], "folder": folder.relative_to(ROOT).as_posix()}
        if record["role"] == "ib1000":
            item["feature_counts"] = gml_counts(folder)
        if record["role"] == "lidar_dtm_2020":
            terrain.append(folder)
        catalog.append(item)
        print("Prepared:", path.name, flush=True)
    output = ROOT / "gis" / f"high_quality_{prefix}"
    output.mkdir(parents=True, exist_ok=True)
    dtm = terrain_crop(terrain, manifest["bounds_epsg2326"], output, prefix)
    ib1000_folders = sorted((raw / "extracted").glob("ib1000_6-NE-*"))
    axis_check = axis_order_check(raw, ib1000_folders, manifest["bounds_epsg2326"])
    ib1000_layers = clip_ib1000(raw, ib1000_folders, manifest["bounds_epsg2326"], output, prefix)
    if args.scope == "pilot":
        orthophoto = crop_orthophoto(raw, catalog, bounds, output)
    else:
        from prepare_full_loop_data import mosaic_orthophotos
        orthophoto = mosaic_orthophotos(raw, catalog, bounds, output)
    buildings = json.loads((raw / "index/buildings_features.json").read_text(encoding="utf-8"))["features"]
    rows = []
    for feature in buildings:
        attrs = feature["attributes"]
        base, top = attrs.get("BaseHeight"), attrs.get("TopHeight")
        valid = isinstance(base, (int, float)) and isinstance(top, (int, float)) and top > base
        rows.append({"object_id": attrs.get("OBJECTID"), "building_id": attrs.get("BuildingID"),
                     "base_height": base, "top_height": top,
                     "derived_height_m": top - base if valid else "", "needs_height_review": not valid})
    with (output / "building_height_review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    orthophoto_summary_record = orthophoto_summary(raw, catalog, bounds) if args.scope == "pilot" else {}
    orthophoto_summary_record.update(orthophoto)
    report = {"acquisition_status": manifest["status"], "prepared_archives": catalog, "terrain": dtm,
              "orthophoto": orthophoto_summary_record,
              "iB1000_axis_order_check": axis_check,
              "iB1000_pilot_layers" if args.scope == "pilot" else "iB1000_full_loop_layers": ib1000_layers,
              "building_footprints": clip_buildings(raw, bounds, output, prefix),
              "buildings": {"records": len(rows), "valid_base_top_pairs": sum(not r["needs_height_review"] for r in rows),
                            "height_review_required": sum(r["needs_height_review"] for r in rows)},
              "ib1000_dictionary_interpretation": {
                  "street_types": {"HIG": "Highway", "MAR": "Main Road", "RER": "Restricted Road",
                                   "ROB": "Road Bridge", "SER": "Secondary Road", "SLR": "Slip Road",
                                   "TRA": "Track", "TUN": "Tunnel"},
                  "spot_heights": {"SHG": "Ground-level spot height", "SHE": "Top level of elevated structure"},
                  "transport_line_types": {"FY": "Flyover/elevated road/bridge",
                                           "FYU": "Flyover beneath another elevated structure",
                                           "TUR": "Vehicle or railway tunnel", "RM": "Road margin",
                                           "RMU": "Road margin below elevated structures"},
                  "use_note": "Use code and display-status fields. Cartographic transport lines are not road-centreline or drivable-surface geometry."},
              "scope": "Source readiness only. Classification, elevations, road and facade authoring remain to be reviewed."}
    if args.scope == "full-loop":
        from prepare_full_loop_data import review_route_sources
        report["scope_id"] = args.scope
        report["bounds_epsg2326"] = bounds
        report["route_source_review"] = review_route_sources(output, bounds)
    save(ROOT / "reports" / ("map_source_readiness.json" if args.scope == "pilot" else
                              "full_loop_source_readiness.json"), report)
    print(json.dumps({"prepared_archives": len(catalog), "terrain": dtm["shape"], "buildings": report["buildings"]}, indent=2))


if __name__ == "__main__":
    main()
