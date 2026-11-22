"""Prepare the whole-Hong-Kong geographic master and all README exam-route audits.

Retained source snapshots remain unchanged. Large geographic outputs stay in
ignored gis/. This does not create/install a KN5 or claim finished road geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/python_deps"))
sys.path.insert(0, str(ROOT.parents[1] / "tools"))

import numpy as np
from PIL import Image, ImageDraw
from shapely import STRtree, prepare
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.ops import transform

import prepare_geodata as foundation
from collect_build_data import TILE_FIELDS, digest
from prepare_hd_map import CENTRES
from research_quality_sources import DATASETS, inspect_dataset, public, save


def compact(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


class MasterReader(foundation.osmium.SimpleHandler):
    """Avoid a Python callback for every unneeded OSM node in the territory."""
    def __init__(self):
        super().__init__()
        self.roads, self.buildings, self.coast = [], [], []
        self.invalid_ways = 0
        self.building_relations_skipped = 0

    def way(self, way):
        foundation.ReadOSM.way(self, way)

    def relation(self, relation):
        foundation.ReadOSM.relation(self, relation)


def prepare_roads(output):
    boundary = foundation.read_complete_boundary(ROOT / "source/hong-kong-boundary-913110.osm")
    # Reuse the existing reader, extending its building window to the full boundary.
    # Use a cheap envelope while reading. Apply the precise prepared boundary
    # once afterwards rather than intersecting its coastline with every building.
    foundation.BBOX = box(*boundary.bounds)
    foundation.REG_WGS_BOUNDS = transform(foundation.TO_WGS.transform, boundary).bounds
    reader = MasterReader()
    print("Reading retained whole-Hong-Kong PBF...", flush=True)
    reader.apply_file(str(ROOT / "source/hong-kong-latest.osm.pbf"), locations=True, idx="flex_mem")
    prepare(boundary)
    print(f"Read {len(reader.roads)} road ways and {len(reader.buildings)} building areas; clipping...", flush=True)
    buildings = []
    for building in reader.buildings:
        geometry = foundation.shape(building["geometry"])
        if not boundary.intersects(geometry):
            continue
        if not boundary.covers(geometry):
            building = dict(building, geometry=mapping(geometry.intersection(boundary)))
        buildings.append(building)
    records, lengths, regions = [], Counter(), {}
    for osm_id, tags, line, refs in reader.roads:
        if not boundary.intersects(line):
            continue
        ref_lookup = {(round(e, 3), round(n, 3)): ref for (e, n), ref in zip(line.coords, refs)}
        clipped = line if boundary.covers(line) else line.intersection(boundary)
        for part_index, part in enumerate(foundation.line_parts(clipped)):
            access = foundation.access_state(tags)
            width, width_source = foundation.road_width(tags)
            xy = [[round(e, 3), round(n, 3)] for e, n in part.coords]
            record = {"osm_id": osm_id, "part": part_index, "tags": tags, "xy": xy,
                      "node_refs": [ref_lookup.get(tuple(p)) for p in xy],
                      "access_state": access, "width_m": width, "width_source": width_source,
                      "length_m": part.length, "clipped_at_boundary": not part.equals(line),
                      "grade_review_required": tags.get("bridge", "no") != "no" or
                      tags.get("tunnel", "no") != "no" or tags.get("layer", "0") != "0"}
            records.append(record)
            lengths[access] += part.length
            x0, y0, x1, y1 = part.bounds
            for x in range(math.floor(x0 / 6000), math.floor(x1 / 6000) + 1):
                for y in range(math.floor(y0 / 6000), math.floor(y1 / 6000) + 1):
                    core = box(x * 6000, y * 6000, (x + 1) * 6000, (y + 1) * 6000)
                    segments = foundation.line_parts(part.intersection(core))
                    if not segments:
                        continue
                    region_id = f"HK_E{x * 6}_N{y * 6}"
                    region = regions.setdefault(region_id, {"id": region_id,
                        "bounds_epsg2326": list(core.bounds), "origin_epsg2326": [x * 6000, y * 6000],
                        "road_parts": 0, "road_line_m": 0., "exam_centres": []})
                    region["road_parts"] += len(segments)
                    region["road_line_m"] += sum(s.length for s in segments)
    compact(output / "hk_roads_grid.json", {"crs": "EPSG:2326", "units": "metres", "roads": records})
    compact(output / "hk_buildings_grid.json", {"crs": "EPSG:2326", "buildings": buildings,
            "limitations": "Closed OSM building ways only; multipolygon building relations deferred; heights unverified"})
    compact(output / "hk_boundary_grid.json", {"crs": "EPSG:2326", "geometry": mapping(boundary)})
    summary = {"master_road_parts": len(records), "simple_building_areas": len(buildings),
               "deferred_building_relations": reader.building_relations_skipped,
               "invalid_source_ways_skipped": reader.invalid_ways,
               "road_line_km_by_access": {k: round(v / 1000, 3) for k, v in lengths.items()},
               "grade_review_road_parts": sum(r["grade_review_required"] for r in records),
               "estimated_width_road_parts": sum(r["width_source"] != "osm_width" for r in records)}
    return boundary, records, regions, summary


def audit_exam_routes(records, regions, output):
    catalog = json.loads((ROOT.parents[1] / "asset/routes/all_road_test_routes.json").read_text(encoding="utf-8"))
    named = {}
    for record in records:
        for key in ("name", "name:zh", "name:zh-Hant"):
            name = record["tags"].get(key)
            if name and any("\u4e00" <= c <= "\u9fff" for c in name):
                named.setdefault(name, []).append(record)
    aliases = {"靠背窩道": "靠背壟道", "右轉靠江蘇街": "右轉江蘇街"}
    centres, audits = [], []
    for centre in catalog["test_centres"]:
        cid = centre["id"]
        config = CENTRES[cid]
        e, n = foundation.TO_GRID.transform(config["lon"], config["lat"])
        region_id = f"HK_E{math.floor(e / 6000) * 6}_N{math.floor(n / 6000) * 6}"
        if region_id in regions:
            regions[region_id]["exam_centres"].append(cid)
        centre_rows = []
        for rid in centre["known_route_ids"]:
            route = catalog["routes"][rid]
            steps = []
            for original in route["instructions"]:
                instruction = original
                for old, new in aliases.items():
                    instruction = instruction.replace(old, new)
                matches = []
                for name, ways in named.items():
                    if name not in instruction:
                        continue
                    candidates = [r for r in ways if LineString(r["xy"]).distance(Point(e, n)) <= 3500]
                    if candidates:
                        matches.append({"name": name, "osm_way_ids": sorted({r["osm_id"] for r in candidates})})
                # A short substring must not hide a longer matching street name.
                matches = [m for m in matches if not any(m["name"] != k["name"] and
                           m["name"] in k["name"] for k in matches)]
                steps.append({"instruction": original, "normalised": instruction,
                              "candidate_streets": matches,
                              "status": "name_candidates_only" if matches else "needs_route_or_manoeuvre_review"})
            audit = {"route_id": rid, "centre": cid, "catalog_status": route.get("status"),
                     "source_url": route.get("source"), "steps": steps,
                     "steps_with_name_candidates": sum(bool(s["candidate_streets"]) for s in steps),
                     "continuous_driving_route_validated": False}
            audits.append(audit)
            centre_rows.append(audit)
        issues = ["Approximate legacy centre coordinate; gate/start position requires verification",
                  "Text instructions are not a connected lane-level route"]
        if cid == "wing_hau_street":
            issues.append("LOCATION_CONFLICT: retained OSM Wing Hau Street / 永孝街 is in Kwai Chung, outside the legacy Kowloon centre window; resolve before modelling")
        centres.append({"id": cid, "name": centre["display_name"], "catalog_routes": len(centre_rows),
                        "approximate_location_epsg2326": [e, n], "candidate_region": region_id,
                        "steps_with_name_candidates": sum(r["steps_with_name_candidates"] for r in centre_rows),
                        "issues": issues})
    compact(output / "exam_route_name_candidates.json", {"centres": centres, "routes": audits,
            "note": "Name matching only. Do not use this as a validated navigation or exam route."})
    return centres, len(audits)


def official_indexes(boundary, records, raw, refresh):
    datasets = dict(DATASETS, individualised_models="landsd_rcd_1671676915450_88604")
    datasets.pop("buildings")  # Do not issue an unbounded territory-wide building-attribute query.
    local = {}
    for path in (ROOT / "source").glob("map_build*/local_manifest.json"):
        for r in json.loads(path.read_text(encoding="utf-8"))["files"]:
            if r.get("status") == "PASS" and r.get("local_path"):
                p = Path(r["local_path"])
                if p.is_file() and p.stat().st_size == r["bytes"]:
                    local[r["name"]] = r
    def index(item):
        name, dataset_id = item
        folder = raw / "index"
        cache = folder / f"{name}_features.json"
        if refresh or not cache.exists():
            _, _, rows = inspect_dataset(item, boundary.bounds, folder)
        else:
            rows = json.loads(cache.read_text(encoding="utf-8"))["features"]
        return name, dataset_id, rows
    tree = STRtree([LineString(r["xy"]) for r in records])
    summaries, queue = {}, []
    with ThreadPoolExecutor(max_workers=3) as pool:
        for name, dataset_id, rows in pool.map(index, datasets.items()):
            field, link = TILE_FIELDS[name]
            selected, retained = 0, 0
            for row in rows:
                rings = row["geometry"].get("rings", [])
                if not rings:
                    raise ValueError("Expected polygon source-tile index")
                tile = Polygon(rings[0])
                hits = tree.query(tile.buffer(160), predicate="intersects")
                if not len(hits):
                    continue
                selected += 1
                attrs = row["attributes"]
                filename = f"{name}_{attrs[field]}.zip"
                cached = local.get(filename)
                retained += bool(cached)
                queue.append({"dataset": name, "sheet": attrs[field], "source_url": public(attrs[link]),
                              "road_parts_within_160m": len(hits),
                              "state": "local_size_matches_previous_manifest" if cached else "not_acquired",
                              "local_manifest_sha256": cached["sha256"] if cached else None})
            summaries[name] = {"dataset_id": dataset_id, "indexed_tiles": len(rows),
                               "road_corridor_tiles": selected, "local_tiles_size_matched": retained,
                               "tiles_not_acquired": selected - retained}
            print(f"Official index: {name}: {selected} road tiles / {retained} local", flush=True)
    compact(raw / "road_tile_acquisition_queue.json", queue)
    return summaries


def overview(boundary, records, centres, output):
    west, south, east, north = boundary.bounds
    width, height = 1800, 1300
    scale = min((width - 70) / (east - west), (height - 100) / (north - south))
    def xy(e, n):
        return 35 + (e - west) * scale, 65 + (north - n) * scale
    image = Image.new("RGB", (width, height), (17, 28, 37))
    draw = ImageDraw.Draw(image)
    for record in records:
        color = (70, 188, 173) if record["access_state"] == "public_candidate" else (170, 111, 60)
        draw.line([xy(e, n) for e, n in record["xy"]], fill=color, width=1)
    for i, centre in enumerate(centres, 1):
        x, y = xy(*centre["approximate_location_epsg2326"])
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 220, 90))
        draw.text((x + 6, y - 13), str(i), fill="white")
    draw.text((30, 18), "HONG KONG 1:1 - geographic road master / not a finished game map", fill="white")
    draw.text((30, 38), "Teal: motor-road candidates | Amber: restricted/review | Yellow: legacy exam-centre locations", fill="white")
    image.save(output / "hong_kong_master_overview.png")


def prepare_master_terrain(output):
    path = ROOT / "source/Whole_HK_DTM_5m.zip"
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError("Whole-Hong-Kong DTM archive CRC failed")
        name = next(n for n in archive.namelist() if n.lower().endswith(".asc"))
        with archive.open(name) as stream:
            header = {}
            for _ in range(6):
                key, value = stream.readline().decode("ascii").split()
                header[key.lower()] = float(value)
            width, height = int(header["ncols"]), int(header["nrows"])
            grid = np.empty((height, width), dtype=np.float32)
            for row in range(height):
                values = np.fromstring(stream.readline().decode("ascii"), sep=" ", dtype=np.float32)
                if len(values) != width:
                    raise ValueError("Truncated master DTM row")
                grid[row] = values
    cell = header["cellsize"]
    west, north = header["xllcorner"], header["yllcorner"] + height * cell
    np.savez_compressed(output / "hk_terrain_5m.npz", z=grid, west_edge=west, north_edge=north,
                        x_first_center=west + cell / 2, y_first_center=north - cell / 2,
                        cell_m=cell, nodata=header["nodata_value"], horizontal_epsg=2326)
    return {"file": "gis/hong_kong_master/hk_terrain_5m.npz", "shape": [height, width],
            "cell_m": cell, "extent_edges_epsg2326": [west, header["yllcorner"], west + width * cell, north],
            "nodata_pixels": int((grid == header["nodata_value"]).sum()),
            "processing": "Full retained native grid; no resampling or elevation offset",
            "limits": "Historical 5 m DTM with stated +/-5 m accuracy at 90% confidence; not road-deck survey data"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-index", action="store_true")
    args = parser.parse_args()
    output, raw = ROOT / "gis/hong_kong_master", ROOT / "source/hong_kong_master"
    output.mkdir(parents=True, exist_ok=True)
    boundary, records, regions, summary = prepare_roads(output)
    centres, routes = audit_exam_routes(records, regions, output)
    for region in regions.values():
        region["road_line_km"] = round(region.pop("road_line_m") / 1000, 3)
        region["stage"] = "source_inventory_only"
    compact(output / "regions.json", {"crs": "EPSG:2326", "core_size_m": 6000,
            "note": "Production regions; no runtime streaming or seamless transition implied",
            "regions": sorted(regions.values(), key=lambda r: (not bool(r["exam_centres"]), r["id"]))})
    overview(boundary, records, centres, output)
    summary["terrain"] = prepare_master_terrain(output)
    summary.update(official_source_indexes=official_indexes(boundary, records, raw, args.refresh_index))
    sources = []
    for name in ("hong-kong-latest.osm.pbf", "hong-kong-boundary-913110.osm", "Whole_HK_DTM_5m.zip"):
        path = ROOT / "source" / name
        sources.append({"file": "source/" + name, "bytes": path.stat().st_size, "sha256": digest(path)})
    summary.update(scope="Whole-Hong-Kong retained motor-road inventory, regional production queue and README exam-route audit",
                   prepared_hong_kong_date=str(datetime.now(timezone(timedelta(hours=8))).date()),
                   horizontal_crs="EPSG:2326", sources=sources,
                   regional_cores_with_roads=len(regions), exam_centres=len(centres), exam_route_records=routes,
                   exam_centre_review=centres, geographic_outputs="gis/hong_kong_master/",
                   source_tile_queue="source/hong_kong_master/road_tile_acquisition_queue.json",
                   limitations=["Source preparation only; no new installed track or collision mesh.",
                    "OSM coverage is not proof every real-world road is present; compare the retained TD network.",
                    "Line lengths count carriageways separately and include review roads; not official road mileage.",
                    "Building relations, bridge decks, tunnels, widths, facades and connected exam routes need production review.",
                    "Detailed tile downloads are queued, not all acquired. Local size matches are not a fresh hash/CRC verification."])
    save(ROOT / "reports/hong_kong_master_readiness.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("exam_centre_review", "sources")}, indent=2))


if __name__ == "__main__":
    main()
