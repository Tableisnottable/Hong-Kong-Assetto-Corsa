"""Use existing original Route Twisk AI loops in CSP Traffic Planner.

Only the original HK51/uphill/downhill layouts are supported. The repack uses
a different road network and needs separately recorded lanes. Original AI
splines are never changed. Road snapping happens in CSP when loading the lane.
"""
import argparse
import datetime
import io
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from prepare_kmb_ai_grid import ROOT, write_backed_up
from repair_omsi_bus_physics import AC, ini


def lane_from_ai(path):
    raw = path.read_bytes()
    version, count, _, _ = struct.unpack_from("<4i", raw)
    if version != 7 or count < 20 or len(raw) < 16 + count * 20:
        raise ValueError("Unsupported/truncated AI line")
    points = np.array([struct.unpack_from("<3f", raw, 16 + i * 20) for i in range(count)])
    if not np.isfinite(points).all() or np.linalg.norm(points[0] - points[-1]) > 3:
        raise ValueError("An existing closed traffic loop is required")
    if np.linalg.norm(np.diff(points, axis=0), axis=1).max() > 5:
        raise ValueError("AI line has a discontinuity")
    # Keep the recorded route; don't invent offsets or reconnect opposite lanes.
    return {"name": "Route Twisk existing AI traffic loop", "id": 1, "loop": True,
            "role": 3, "priorityOffset": 0, "speedLimit": 40,
            "points": points.tolist(), "params": {"allowLaneChanges": False, "allowUTurns": False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/KMB_AI")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.install:
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV"], capture_output=True, text=True, check=True)
        if '"acs.exe"' in result.stdout.lower():
            raise RuntimeError("Close AC before updating traffic routes")
    reports = []
    backup = args.output / "backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for layout in ("route_twisk_HK51", "route_twisk_traffic_uphill", "route_twisk_traffic_downhill"):
        source = args.ac / "content/tracks/route_twisk" / layout
        lane = lane_from_ai(source / "ai/fast_lane.ai")
        network = {"lanes": [lane], "intersections": [], "areas": [], "rules": {"laneRoles": [
            {"name": "Parking", "priority": -8, "speedLimit": 20},
            {"name": "Secondary", "priority": -4, "speedLimit": 30},
            {"name": "Main", "priority": 0, "speedLimit": 40},
            {"name": "Highway", "priority": 4, "speedLimit": 70}]}}
        out = args.output / "planner_tracks" / layout
        out.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(network, separators=(",", ":")).encode("utf-8")
        (out / "traffic.json").write_bytes(payload)
        cp = ini(source / "data/surfaces.ini")
        cp["SURFACE_0"]["WAV_PITCH"] = "extended-0"
        if not cp.has_section("_SCRIPTING_PHYSICS"):
            cp.add_section("_SCRIPTING_PHYSICS")
        cp["_SCRIPTING_PHYSICS"]["ALLOW_TOOLS"] = "1"
        stream = io.StringIO()
        cp.write(stream, space_around_delimiters=False)
        surfaces = stream.getvalue().encode("utf-8")
        (out / "surfaces.ini").write_bytes(surfaces)
        if args.install:
            dest = source / "data"
            if (dest / "traffic.json").exists() and (dest / "traffic.json").read_bytes() != payload:
                raise ValueError("Existing traffic route differs; preserve and review before replacing: " + str(dest))
            write_backed_up(dest / "surfaces.ini", surfaces, backup / layout)
            write_backed_up(dest / "traffic.json", payload, backup / layout)
        reports.append({"layout": layout, "points": len(lane["points"]), "loop": True,
                        "installed": args.install, "backup": str(backup / layout),
                        "runtime_road_snapping": "pending CSP load and user test"})
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"status": "PASS", "layouts": reports, "repack": "no verified lane alignment; not modified"}
    (args.output / "planner_routes_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
