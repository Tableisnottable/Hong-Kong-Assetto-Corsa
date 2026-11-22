"""Full-loop georeferenced imagery and source-review helpers; no game export."""
from __future__ import annotations

import csv
import json
import math

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString, shape
from shapely.ops import unary_union

from collect_build_data import ROOT


def mosaic_orthophotos(raw, catalog, bounds, output):
    """Copy native pixel windows from every intersecting sheet, with no resampling."""
    west, south, east, north = bounds
    cell = .25
    width, height = round((east - west) / cell), round((north - south) / cell)
    canvas = Image.new("RGB", (width, height))
    covered = np.zeros((height, width), dtype=bool)
    features = json.loads((raw / "index/tdop_features.json").read_text(encoding="utf-8"))["features"]
    by_sheet = {f["attributes"]["SHEETNO"]: f["attributes"] for f in features}
    sources = []
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        for item in catalog:
            if item["role"] != "tdop":
                continue
            folder = ROOT / item["folder"]
            sheet = folder.name.removeprefix("tdop_")
            # Select a matched TIFF/world-file pair; reject ambiguous source rasters.
            worlds = sorted(folder.rglob("*.tfw"))
            pairs = [(p.with_suffix(".tif"), p) for p in worlds if p.with_suffix(".tif").is_file()]
            if len(pairs) != 1:
                raise ValueError("Expected one orthophoto/world-file pair: " + sheet)
            image_path, world = pairs[0]
            a, d, b, e, xc, yc = map(float, world.read_text(encoding="ascii").split())
            if (a, d, b, e) != (cell, 0., 0., -cell):
                raise ValueError("Expected north-up 0.25 m orthophoto: " + sheet)
            tw, tn = xc - cell / 2, yc + cell / 2
            with Image.open(image_path) as image:
                xw, yn = max(west, tw), min(north, tn)
                xe, ys = min(east, tw + image.width * cell), max(south, tn - image.height * cell)
                if xe <= xw or yn <= ys:
                    continue
                coordinates = [(xw - tw) / cell, (tn - yn) / cell,
                               (xe - tw) / cell, (tn - ys) / cell,
                               (xw - west) / cell, (north - yn) / cell]
                if any(abs(v - round(v)) > 1e-7 for v in coordinates):
                    raise ValueError("Orthophoto windows do not align on native pixel edges")
                left, top, right, bottom, col, row = map(round, coordinates)
                patch = image.crop((left, top, right, bottom)).convert("RGB")
                region = covered[row:row + patch.height, col:col + patch.width]
                if region.any():
                    raise ValueError("Overlapping orthophoto windows require explicit date/source selection")
                canvas.paste(patch, (col, row))
                region[:] = True
                sources.append({"sheet": sheet, "photograph_date": by_sheet[sheet].get("DATE_OF_PHOTOGRAPH"),
                                "source_image": image_path.relative_to(ROOT).as_posix(),
                                "copied_window_pixels": [left, top, right, bottom],
                                "source_extent_epsg2326": [tw, tn - image.height * cell,
                                                          tw + image.width * cell, tn]})
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit
    missing = int((~covered).sum())
    if missing:
        raise ValueError(f"Orthophoto mosaic has {missing} uncovered pixels")
    path = output / "full_loop_orthophoto.jpg"
    canvas.save(path, quality=95, subsampling=0, optimize=True)
    path.with_suffix(".jgw").write_text(
        f"{cell:.9f}\n0.000000000\n0.000000000\n{-cell:.9f}\n"
        f"{west + cell / 2:.9f}\n{north - cell / 2:.9f}\n", encoding="ascii")
    path.with_suffix(".crs.txt").write_text("EPSG:2326\n", encoding="ascii")
    return {"dataset_id": "landsd_rcd_1701762716904_4826", "sources": sources,
            "crop_file": path.relative_to(ROOT).as_posix(),
            "world_file": path.with_suffix(".jgw").relative_to(ROOT).as_posix(),
            "crs_file": path.with_suffix(".crs.txt").relative_to(ROOT).as_posix(),
            "dimensions_pixels": [width, height], "bounds_epsg2326": bounds,
            "ground_sample_distance_m": cell, "uncovered_pixels": missing,
            "pixel_centres_epsg2326_first": [west + cell / 2, north - cell / 2],
            "alignment": "PASS", "processing": "Native pixel-window mosaic; no resampling; JPEG quality 95"}


def quantiles(values):
    return {"min": float(np.min(values)), "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)), "max": float(np.max(values))} if len(values) else None


def review_route_sources(output, bounds):
    source = ROOT / "driving_test/source/test_loop_source.json"
    route = json.loads(source.read_text(encoding="utf-8"))
    line = LineString(route["xy"])
    count = math.ceil(line.length / 2)
    chainages = np.linspace(0, line.length, count, endpoint=False)
    points = [line.interpolate(float(s)) for s in chainages]
    with np.load(output / "full_loop_dtm_05m.npz") as data:
        terrain = data["z"].copy()
        cell = float(data["cell_m"])
        west, north = float(data["west_edge"]), float(data["north_edge"])

    def terrain_at(p):
        col, row = int(math.floor((p.x - west) / cell)), int(math.floor((north - p.y) / cell))
        if not (0 <= row < terrain.shape[0] and 0 <= col < terrain.shape[1]):
            return None
        value = float(terrain[row, col])
        return value if math.isfinite(value) else None

    heights = [terrain_at(p) for p in points]
    if any(h is None for h in heights):
        raise ValueError("LiDAR does not support every retained route sample")
    streets = json.loads((output / "iB1000_StreetCentreLines_full_loop_grid.json").read_text(encoding="utf-8"))
    street_union = unary_union([shape(f["geometry"]) for f in streets["features"]])
    if street_union.is_empty:
        raise ValueError("No official street linework in route envelope")
    distances = np.asarray([p.distance(street_union) for p in points])
    with (output / "route_source_review.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_chainage_m", "easting", "northing", "native_dtm_m",
                         "distance_to_ib1000_street_m", "centreline_review_over_5m"])
        writer.writerows((round(s, 3), p.x, p.y, h, round(float(d), 3), bool(d > 5))
                        for s, p, h, d in zip(chainages, points, heights, distances))

    # Compare native ground references without applying an inferred vertical correction.
    spots = json.loads((output / "iB1000_SpotHeight_full_loop_grid.json").read_text(encoding="utf-8"))
    deltas, spot_rows = [], []
    for feature in spots["features"]:
        props = feature["properties"]
        p = shape(feature["geometry"])
        if props.get("FEATURETYPE") != "SHG":
            continue
        height = props.get("HEIGHTVALUE")
        if height is None:
            # Retain the attributes; never guess an undocumented height field.
            continue
        try:
            h = float(height)
        except (ValueError, TypeError):
            continue
        dtm = terrain_at(p)
        if dtm is None or not math.isfinite(h):
            continue
        deltas.append(dtm - h)
        spot_rows.append([feature["id"], p.x, p.y, h, dtm, dtm - h, props.get("DISPLAYSTATUS")])
    with (output / "spot_height_comparison.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source_id", "easting", "northing", "ib1000_height", "native_dtm",
                         "dtm_minus_spot_m", "display_status"])
        writer.writerows(spot_rows)

    buildings = json.loads((output / "LandsD_building_footprints_full_loop_grid.json").read_text(encoding="utf-8"))
    priorities = []
    for feature in buildings["features"]:
        props = feature["properties"]
        distance = shape(feature["geometry"]).distance(line)
        priorities.append({"object_id": feature["id"], "building_id": props.get("BuildingID"),
                           "distance_to_source_route_m": round(distance, 3),
                           "priority": "near_0_60m" if distance <= 60 else "context",
                           "height_review_required": props["HEIGHT_REVIEW_REQUIRED"]})
    priorities.sort(key=lambda row: row["distance_to_source_route_m"])
    with (output / "building_authoring_queue.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["object_id", "building_id", "distance_to_source_route_m",
                                                   "priority", "height_review_required"])
        writer.writeheader()
        writer.writerows(priorities)

    with Image.open(output / "full_loop_orthophoto.jpg") as image:
        preview = image.copy()
    preview.thumbnail((1200, 1800))
    draw = ImageDraw.Draw(preview)
    sx, sy = preview.width / (bounds[2] - bounds[0]), preview.height / (bounds[3] - bounds[1])
    coords = [((p[0] - bounds[0]) * sx, (bounds[3] - p[1]) * sy) for p in route["xy"]]
    draw.line(coords, fill=(255, 220, 0), width=4)
    draw.rectangle((8, 8, min(preview.width - 8, 680), 48), fill=(15, 25, 30))
    draw.text((18, 18), "KAM TIN: full retained source loop / yellow = route reference", fill="white")
    preview.save(output / "full_loop_source_overview.jpg", quality=92)
    near = [r for r in priorities if r["priority"] == "near_0_60m"]
    return {"route_file": source.relative_to(ROOT).as_posix(),
            "route_basis": "Retained OSM source polyline; not the filleted 3.445 km installed collision mesh",
            "source_length_m": line.length, "samples": count, "sample_spacing_m": line.length / count,
            "terrain_supported_samples": count, "terrain_sample_coverage_percent": 100.,
            "distance_to_ib1000_street_m": quantiles(distances),
            "samples_over_5m_from_official_street": int((distances > 5).sum()),
            "ground_spots_compared": len(deltas), "dtm_minus_ground_spot_m": quantiles(deltas),
            "near_route_buildings_0_60m": len(near),
            "near_route_buildings_needing_height_review": sum(r["height_review_required"] for r in near),
            "review_files": [(output / n).relative_to(ROOT).as_posix() for n in
                             ("route_source_review.csv", "spot_height_comparison.csv",
                              "building_authoring_queue.csv", "full_loop_source_overview.jpg")],
            "limits": ["Source alignment and terrain coverage only; no proof of road collision, public access or finished scenery.",
                       "Spot samples use the containing 0.5 m DTM pixel; dates and display status differ. No vertical correction applied.",
                       "Building priority uses footprint distance; it does not establish visibility or validate model geometry."]}
