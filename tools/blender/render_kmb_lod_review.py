"""Render full detail, LOD 2 and LOD 4 for six buses, without opening AC.

blender --background --factory-startup --python tools/blender/render_kmb_lod_review.py -- STAGED_RUN
"""
import argparse
from pathlib import Path
import sys

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_bus_preview
from prepare_kmb_ai_grid import buses
from repair_omsi_bus_physics import AC


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('staged', type=Path)
    parser.add_argument('--ac', type=Path, default=AC)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    for bus in buses():
        car = args.ac / 'content/cars' / bus['id']
        for level in (0, 2, 4):
            source = car / (car.name + '.kn5') if level == 0 else args.staged / car.name / f'{car.name}_lod{level}.kn5'
            out = args.staged / 'previews' / car.name / f'lod{level}'
            bpy.data.orphans_purge(do_recursive=True)
            sys.argv = ['blender', '--', str(car), str(out), bus['skin'], '--model', str(source)]
            render_bus_preview.main()


if __name__ == '__main__':
    main()
