"""Create a separate Highlands Short layout with 12 bus-sized spawn slots.

Reuses the installed track and its road/AI data. Only spawn markers are
renumbered: every second pit and alternate grid rows are retained. Generated
track files and UI remain local. Does not change the original layout or race.ini.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np
from kn5_tools import Kn5
from prepare_kmb_ai_grid import buses, write_backed_up
from repair_omsi_bus_physics import AC, world_vertices

LAYOUT = "layout_short_kmb"
OWNER = "KMB_BUS_SPACING_V1"


def spawn_matrices(model, prefix):
    result = {}

    def visit(node, parent=np.eye(4)):
        world = node.matrix @ parent if node.kind == 1 else parent
        if node.kind == 1 and re.fullmatch(prefix + r"\d+", node.name):
            result[int(node.name.removeprefix(prefix))] = world
        for child in node.children:
            visit(child, world)

    visit(model.root)
    return result


def overlap(a, b, half):
    """Separating-axis test of conservative horizontal bus collision boxes."""
    local = np.array([[-half[0], -half[1]], [-half[0], half[1]],
                      [half[0], half[1]], [half[0], -half[1]]])
    polygons = [local @ m[np.ix_([0, 2], [0, 2])] + m[3, [0, 2]] for m in (a, b)]
    for polygon in polygons:
        for edge in (polygon[1] - polygon[0], polygon[2] - polygon[1]):
            axis = np.array([-edge[1], edge[0]])
            x, y = [p @ axis for p in polygons]
            if x.max() <= y.min() or y.max() <= x.min():
                return False
    return True


def collisions(slots, half):
    return [[i, j] for i in sorted(slots) for j in sorted(slots)
            if i < j and overlap(slots[i], slots[j], half)]


def prepare(ac, output, install):
    track = ac / "content/tracks/ks_highlands"
    model = Kn5(track / "9.kn5")
    half = np.zeros(2)
    for bus in buses():
        hull = Kn5(ac / "content/cars" / bus["id"] / "collider.kn5")
        points = np.concatenate(list(world_vertices(hull.root)))
        half = np.maximum(half, np.abs(points[:, [0, 2]]).max(0))
    half += .25  # Include half a metre of separation between collision bodies.
    before = {kind: collisions(spawn_matrices(model, "AC_" + kind + "_"), half)
              for kind in ("PIT", "START")}
    chosen = {"PIT": list(range(0, 24, 2)),
              "START": [i for i in range(24) if (i // 2) % 2 == 0]}
    for _, node in model.root.walk():
        match = re.fullmatch(r"AC_(PIT|START)_(\d+)", node.name)
        if match:
            kind, number = match[1], int(match[2])
            if number in chosen[kind]:
                node.name = f"AC_{kind}_{chosen[kind].index(number)}"
            else:
                node.name = "KMB_UNUSED_" + node.name
    stage = output / "track"
    stage.mkdir(parents=True, exist_ok=True)
    model.write(stage / "kmb_short_spawns.kn5")
    saved = Kn5(stage / "kmb_short_spawns.kn5")
    after = {}
    for kind in chosen:
        slots = spawn_matrices(saved, "AC_" + kind + "_")
        if set(slots) != set(range(12)):
            raise ValueError("Missing or non-contiguous " + kind + " markers")
        after[kind] = collisions(slots, half)
        if after[kind]:
            raise ValueError("Bus-sized spawn boxes still overlap: " + str(after))
    source = (track / "models_layout_short.ini").read_text(encoding="utf-8-sig")
    if len(re.findall(r"(?im)^FILE=9\.kn5\s*$", source)) != 1:
        raise ValueError("Unexpected Highlands model list")
    source = re.sub(r"(?im)^FILE=9\.kn5(?=\s*$)", "FILE=kmb_short_spawns.kn5", source)
    (stage / f"models_{LAYOUT}.ini").write_text(source, encoding="utf-8")
    shutil.copytree(track / "layout_short", stage / LAYOUT, dirs_exist_ok=True)
    shutil.copytree(track / "ui/layout_short", stage / "ui" / LAYOUT, dirs_exist_ok=True)
    ui_path = stage / "ui" / LAYOUT / "ui_track.json"
    ui = json.loads(ui_path.read_text(encoding="utf-8-sig"))
    ui.update(name="Highlands Short (KMB bus spacing)", pitboxes="12",
              description="Bus test layout: 12 spaced pit bays and grid slots. Original road and AI line.")
    ui_path.write_text(json.dumps(ui, indent=2), encoding="utf-8")
    marker = track / LAYOUT / "kmb_spacing.json"
    if install:
        running = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV", "/NH"],
                                 capture_output=True, text=True, check=True)
        if '"acs.exe"' in running.stdout.lower():
            raise RuntimeError("Close AC before installing the bus test layout")
        if (track / LAYOUT).exists() and (not marker.exists() or
                json.loads(marker.read_text(encoding="utf-8")).get("owner") != OWNER):
            raise ValueError("Existing layout is not owned by this generator")
        backup = output / "backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        for path in stage.rglob("*"):
            if path.is_file():
                rel = path.relative_to(stage)
                # Unowned model/UI collisions must not be overwritten.
                target = track / rel
                if target.exists() and not marker.exists() and target.read_bytes() != path.read_bytes():
                    raise ValueError("Existing unowned file: " + str(target))
        for path in stage.rglob("*"):
            if path.is_file():
                rel = path.relative_to(stage)
                write_backed_up(track / rel, path.read_bytes(), backup / rel.parent)
    report = dict(owner=OWNER, status="PASS", layout=LAYOUT, pitboxes=12,
                  collision_half_extents_with_margin_m=half.tolist(),
                  original_overlapping_slot_pairs=before, new_overlapping_slot_pairs=after,
                  source_model_sha256=hashlib.sha256((track / "9.kn5").read_bytes()).hexdigest(),
                  installed=install, runtime="Pending user test; geometry checks do not prove driving behavior")
    (output / "bus_spacing.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if install:
        marker.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.ac, args.output, args.install), indent=2))
