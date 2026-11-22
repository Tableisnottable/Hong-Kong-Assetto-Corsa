"""Verify prepared regional geography; this is not game/physics validation."""
from __future__ import annotations

import json

import numpy as np

from collect_build_data import ROOT, digest
from research_quality_sources import save


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    master = ROOT / "gis/hong_kong_master"
    road_file, region_file = master / "hk_roads_grid.json", master / "regions.json"
    roads = json.loads(road_file.read_text(encoding="utf-8"))["roads"]
    regions = json.loads(region_file.read_text(encoding="utf-8"))["regions"]
    buildings = json.loads((master / "hk_buildings_grid.json").read_text(encoding="utf-8"))["buildings"]
    building_by_id = {b["osm_id"]: b for b in buildings}
    source_nodes, source_parts = {}, {}
    for record in roads:
        source_nodes.setdefault(record["osm_id"], set()).update(n for n in record["node_refs"] if n is not None)
        source_parts[(record["osm_id"], record["part"])] = record
    report = json.loads((ROOT / "reports/regional_source_preparation.json").read_text(encoding="utf-8"))
    require(report["source_sha256"] == digest(road_file), "Regional source report is stale")
    master_length = sum(r["length_m"] for r in roads)
    regional_length = sum(r["road_line_km"] * 1000 for r in report["regions"])
    require(abs(master_length - regional_length) < 40, "Regional core road lengths do not conserve the territory inventory")
    portal_refs, hashes = {}, {}
    context_parts = 0
    building_checks = 0
    with np.load(master / "hk_terrain_5m.npz") as source:
        z = source["z"]
        cell, west, north = float(source["cell_m"]), float(source["west_edge"]), float(source["north_edge"])
        for region in regions:
            folder = master / "regions" / region["id"]
            data = json.loads((folder / "roads_grid.json").read_text(encoding="utf-8"))
            require(data["crs"] == "EPSG:2326" and data["origin"] == region["origin_epsg2326"], "Regional coordinate origin changed")
            w, s, e, n = data["context_bounds"]
            for road in data["roads"]:
                require((road["osm_id"], road["part"]) in source_parts, "Unknown source road in region")
                original = source_parts[(road["osm_id"], road["part"])]
                require(road["grade_review_required"] == original["grade_review_required"], "Lost grade separation review flag")
                require(len(road["xy"]) == len(road["node_refs"]), "Road node-reference count differs from geometry")
                for p, ref in zip(road["xy"], road["node_refs"]):
                    require(w - .002 <= p[0] <= e + .002 and s - .002 <= p[1] <= n + .002, "Regional road outside its editing window")
                    require(ref is None or ref in source_nodes[road["osm_id"]], "Fabricated OSM junction reference")
                context_parts += 1
            for portal in json.loads((folder / "boundary_portals.json").read_text(encoding="utf-8")):
                identity = (portal["osm_id"], portal["xy"], portal["source_node_ref"], portal["grade_review_required"])
                if portal["id"] in portal_refs:
                    require(portal_refs[portal["id"]] == identity, "Mismatched shared regional boundary portal")
                portal_refs[portal["id"]] = identity
            local_buildings = json.loads((folder / "building_footprints_grid.json").read_text(encoding="utf-8"))["buildings"]
            for building in local_buildings:
                require(building == building_by_id[building["osm_id"]], "Regional extraction cut or changed a building footprint")
                building_checks += 1
            with np.load(folder / "terrain_5m.npz") as crop:
                require(float(crop["cell_m"]) == cell, "Regional terrain resolution changed")
                cw, cn = float(crop["west_edge"]), float(crop["north_edge"])
                require(abs(float(crop["x_first_center"]) - (cw + cell / 2)) < 1e-7 and
                        abs(float(crop["y_first_center"]) - (cn - cell / 2)) < 1e-7,
                        "Regional terrain has half-pixel shift")
                col, row = round((cw - west) / cell), round((north - cn) / cell)
                values = crop["z"]
                require(np.array_equal(values, z[row:row + values.shape[0], col:col + values.shape[1]], equal_nan=True),
                        "Regional terrain values differ from the native master")
            hashes[region["id"]] = {name: digest(folder / name) for name in
                ("roads_grid.json", "building_footprints_grid.json", "boundary_portals.json", "terrain_5m.npz", "road_review.csv")}
    audit = json.loads((master / "exam_route_name_candidates.json").read_text(encoding="utf-8"))
    require(len(audit["centres"]) == 13 and len(audit["routes"]) == 31, "README exam-route scope lost")
    require(all(not r["continuous_driving_route_validated"] for r in audit["routes"]), "Unreviewed exam routes marked complete")
    result = {"status": "PASS", "scope": "Geographic source and regional extraction integrity only",
              "master_roads_sha256": digest(road_file), "region_manifest_sha256": digest(region_file),
              "checked_regions": len(regions), "checked_context_road_parts": context_parts,
              "checked_intact_context_building_records": building_checks,
              "unique_boundary_portals": len(portal_refs),
              "regional_length_rounding_difference_m": regional_length - master_length,
              "per_region_file_sha256": hashes,
              "limits": ["No new road mesh, collision, KN5, installation, engine appearance or driving was validated.",
                         "Source widths/heights/access, deferred building relations and incomplete exam itineraries still require review."]}
    save(ROOT / "reports/hong_kong_master_verification.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "per_region_file_sha256"}, indent=2))


if __name__ == "__main__":
    main()
