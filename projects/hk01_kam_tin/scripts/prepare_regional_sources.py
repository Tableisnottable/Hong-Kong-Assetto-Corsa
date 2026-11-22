"""Derive regional authoring inputs with shared master coordinates and seam IDs."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from shapely import STRtree
from shapely.geometry import LineString, Point, box, shape

from collect_build_data import ROOT, digest
sys.path.insert(0, str(ROOT / "source/python_deps"))
from prepare_geodata import line_parts
from research_quality_sources import save


def clip_record(record, window):
    line = LineString(record["xy"])
    refs = {tuple(p): ref for p, ref in zip(record["xy"], record["node_refs"])}
    output = []
    for index, part in enumerate(line_parts(line.intersection(window))):
        xy = [[round(e, 3), round(n, 3)] for e, n in part.coords]
        if len(set(map(tuple, xy))) < 2:
            continue
        output.append(dict(record, regional_part=index, xy=xy,
                           node_refs=[refs.get(tuple(p)) for p in xy],
                           length_m=LineString(xy).length,
                           clipped_at_region=not part.equals(line)))
    return output


def portals(record, bounds):
    """Stable identity for where the same source way meets a regional edge."""
    boundary = box(*bounds).boundary
    result = []
    for p, ref in zip(record["xy"], record["node_refs"]):
        if Point(p).distance(boundary) > .0011:
            continue
        token = f"{record['osm_id']}:{p[0]:.3f}:{p[1]:.3f}"
        result.append({"id": hashlib.sha256(token.encode("ascii")).hexdigest()[:20],
                       "osm_id": record["osm_id"], "xy": p, "source_node_ref": ref,
                       "grade_review_required": record["grade_review_required"]})
    return result


def crop_terrain(data, bounds, destination):
    z = data["z"]
    cell = float(data["cell_m"])
    west, north = float(data["west_edge"]), float(data["north_edge"])
    x0, y0, x1, y1 = bounds
    left, right = max(0, math.floor((x0 - west) / cell)), min(z.shape[1], math.ceil((x1 - west) / cell))
    top, bottom = max(0, math.floor((north - y1) / cell)), min(z.shape[0], math.ceil((north - y0) / cell))
    if left >= right or top >= bottom:
        raise ValueError("Regional roads fall outside retained terrain raster")
    crop = z[top:bottom, left:right]
    np.savez_compressed(destination, z=crop, cell_m=cell,
                        west_edge=west + left * cell, north_edge=north - top * cell,
                        x_first_center=west + (left + .5) * cell,
                        y_first_center=north - (top + .5) * cell,
                        nodata=data["nodata"], horizontal_epsg=2326)
    return {"shape": list(crop.shape), "nodata_pixels": int((crop == data["nodata"]).sum())}


def main():
    master = ROOT / "gis/hong_kong_master"
    source = master / "hk_roads_grid.json"
    records = json.loads(source.read_text(encoding="utf-8"))["roads"]
    buildings = json.loads((master / "hk_buildings_grid.json").read_text(encoding="utf-8"))["buildings"]
    building_tree = STRtree([shape(b["geometry"]) for b in buildings])
    regions = json.loads((master / "regions.json").read_text(encoding="utf-8"))["regions"]
    tree = STRtree([LineString(r["xy"]) for r in records])
    summaries, all_portals = [], {}
    with np.load(master / "hk_terrain_5m.npz") as terrain:
        # Decode the territory raster once; NpzFile re-inflates an array each time
        # it is indexed, which is wasteful across dozens of regional crops.
        terrain_snapshot = {key: terrain[key] for key in terrain.files}
        for region in regions:
            core = box(*region["bounds_epsg2326"])
            window = box(*core.buffer(200).bounds)
            selected = tree.query(window, predicate="intersects")
            core_records = [part for i in selected for part in clip_record(records[int(i)], core)]
            context_records = [part for i in selected for part in clip_record(records[int(i)], window)]
            folder = master / "regions" / region["id"]
            folder.mkdir(parents=True, exist_ok=True)
            building_ids = building_tree.query(window, predicate="intersects")
            save(folder / "building_footprints_grid.json", {"crs": "EPSG:2326",
                 "origin": region["origin_epsg2326"],
                 "buildings": [buildings[int(i)] for i in building_ids],
                 "note": "Intact master footprints selected by context intersection; no regional-edge cuts or assigned heights"})
            save(folder / "roads_grid.json", {"crs": "EPSG:2326", "units": "metres",
                 "origin": region["origin_epsg2326"], "core_bounds": region["bounds_epsg2326"],
                 "context_bounds": list(window.bounds), "roads": context_records,
                 "note": "Includes 200 m editing context; clip to coordinated core before release"})
            seam_rows = {p["id"]: p for r in core_records for p in portals(r, region["bounds_epsg2326"])}
            for portal in seam_rows.values():
                all_portals.setdefault(portal["id"], []).append(region["id"])
            save(folder / "boundary_portals.json", list(seam_rows.values()))
            with (folder / "road_review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["osm_id", "access_state", "width_source", "bridge", "tunnel", "layer", "height_review"])
                for record in core_records:
                    tags = record["tags"]
                    writer.writerow([record["osm_id"], record["access_state"], record["width_source"],
                                     tags.get("bridge"), tags.get("tunnel"), tags.get("layer"),
                                     "road_deck_review_required" if record["grade_review_required"] else "terrain_fit_review_required"])
            crop = crop_terrain(terrain_snapshot, window.bounds, folder / "terrain_5m.npz")
            summaries.append({"id": region["id"], "core_road_parts": len(core_records),
                              "context_building_footprints": len(building_ids),
                              "context_road_parts": len(context_records), "boundary_portals": len(seam_rows),
                              "road_line_km": round(sum(r["length_m"] for r in core_records) / 1000, 3),
                              "terrain": crop})
            print(f"Regional inputs: {region['id']} / {len(core_records)} road parts", flush=True)
    seam_counts = Counter(len(set(regions)) for regions in all_portals.values())
    report = {"scope": "Regional road/context and terrain authoring inputs; no playable track export",
              "source_sha256": digest(source), "regions": summaries,
              "portal_region_count_histogram": dict(seam_counts),
              "shared_portals": sum(n > 1 for n in map(len, all_portals.values())),
              "limits": ["Boundary portals establish horizontal source identity only; deck heights and mesh seams remain unbuilt.",
                         "Terrain NoData remains unchanged; bridge/tunnel roads must not inherit ground heights.",
                         "Context overlaps intentionally; no streaming or seamless travel is implemented."]}
    save(ROOT / "reports/regional_source_preparation.json", report)


if __name__ == "__main__":
    main()
