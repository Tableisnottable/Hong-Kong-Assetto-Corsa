"""Build and install four progressively reduced LODs for all six native AC buses.

Traffic Planner uses the same generator through build_kmb_planner_traffic.py.
Requires numpy, Pillow, Node.js, meshoptimizer@1.3.0 (see --meshoptimizer).
Never starts AC. Generated models, reports and backups stay outside Git.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess

import numpy as np
from PIL import Image

from kn5_tools import Kn5, read_u32, read_string
from prepare_kmb_ai_grid import ROOT, buses, write_backed_up
from repair_omsi_bus_physics import AC, bounds, ini, world_vertices

NATIVE_BANDS = (0, 40, 90, 180, 350, 2000)
TRAFFIC_BANDS = (80, 140, 250, 450)
MODULE = ROOT / 'outputs/KMB_20MB/deps/node_modules/meshoptimizer/index.js'
PROTECTED = re.compile(r'destination|hanover|gorba|display|sign|glass|window|windscreen|wheel|whl|rim_|tyre|tire', re.I)
SMALL_INTERIOR = re.compile(r'hammer|charger|rail|grips?|button|ticket|fare|oxygen', re.I)
LARGE_INTERIOR = re.compile(r'chair|seat|dash|strw|steer|cockpit|dpip', re.I)
RATIOS = ((.65, .006), (.55, .018), (.45, .04), (.4, .06))
SIGN_TEXTURE = re.compile(r'destination|hanover|gorba|display|sign|font|led', re.I)


def triangle_count(model):
    return sum(n.index_count // 3 for _, n in model.root.walk() if n.kind in (2, 3))


def texture_payloads(model):
    stream = io.BytesIO(model.prefix)
    stream.seek(10 if model.version <= 5 else 14)
    result = {}
    for _ in range(read_u32(stream)):
        read_u32(stream)
        name = read_string(stream)
        result[name] = stream.read(read_u32(stream))
    return result


def model_bounds(model):
    points = np.concatenate(list(world_vertices(model.root)))
    return np.array([points.min(0), points.max(0)])


def dummy_pivots(model):
    # Traversal order is stable, including duplicate OMSI names.
    return [(p, n.name, n.matrix.tolist()) for p, n in model.root.walk() if n.kind == 1]


def prune_interior(node, level):
    kept, removed = [], 0
    for child in node.children:
        name = child.name
        remove = child.kind == 2 and not child.children and not PROTECTED.search(name) and (
            level >= 2 and SMALL_INTERIOR.search(name) or
            level >= 3 and LARGE_INTERIOR.search(name))
        if remove:
            removed += 1
        else:
            removed += prune_interior(child, level)
            kept.append(child)
    node.children = kept
    return removed


def simplify_level(model, level, work, module):
    work.mkdir(parents=True, exist_ok=True)
    removed = prune_interior(model.root, level)
    nodes, jobs = {}, []
    ratio, error = RATIOS[level - 1]
    for index, (_, node) in enumerate(model.root.walk()):
        if node.kind != 2 or node.index_count <= 36:
            continue
        # Keep the actual text planes and screens intact at every distance.
        if re.search(r'destination|hanover|gorba|display', node.name, re.I):
            continue
        offset = node.vertex_offset + node.vertex_count * node.vertex_stride
        indices = np.frombuffer(node.payload, '<u2', node.index_count, offset + 4).astype('<u4')
        path = work / f'{index}.bin'
        path.write_bytes(struct.pack('<II', node.vertex_count, node.index_count) +
                         node.vertices.astype('<f4').tobytes() + indices.tobytes())
        jobs.append({'id': index, 'input': str(path), 'output': str(path.with_suffix('.indices')),
                     'ratio': ratio, 'error': error})
        nodes[index] = node
    manifest = work / 'jobs.json'
    result = work / 'result.json'
    manifest.write_text(json.dumps({'module': str(module.resolve()), 'jobs': jobs, 'result': str(result)}), encoding='utf-8')
    subprocess.run(['node', str(ROOT / 'tools/simplify_kmb_lods.mjs'), str(manifest)], check=True)
    results = json.loads(result.read_text(encoding='utf-8'))
    for job, check in zip(jobs, results, strict=True):
        node = nodes[job['id']]
        indices = np.fromfile(job['output'], dtype='<u4')
        if check['id'] != job['id'] or not len(indices) or len(indices) % 3 or indices.max() >= node.vertex_count:
            raise ValueError('Invalid meshoptimizer output: ' + node.name)
        if check['error_m'] > error + 1e-5:
            raise ValueError('Meshoptimizer exceeded error budget: ' + node.name)
        if len(indices) >= node.index_count:
            continue
        vertices = node.vertices.copy()
        kept, remapped = np.unique(indices, return_inverse=True)
        end = node.vertex_offset + node.vertex_count * node.vertex_stride
        tail = node.payload[end + 4 + node.index_count * 2:]
        node.payload = bytearray(node.payload[:node.vertex_offset - 4] + struct.pack('<I', len(kept)) +
                                vertices[kept].astype('<f4').tobytes() + struct.pack('<I', len(indices)) +
                                remapped.astype('<u2').tobytes() + tail)
        node.vertex_count, node.index_count = len(kept), len(indices)
        bounds(node)
    return {'removed_interior_meshes': removed, 'max_step_error_m': max((r['error_m'] for r in results), default=0)}


def reduce_textures(model, size):
    stream = io.BytesIO(model.prefix)
    stream.seek(10 if model.version <= 5 else 14)
    updates = {}
    for _ in range(read_u32(stream)):
        read_u32(stream)
        name = read_string(stream)
        raw = stream.read(read_u32(stream))
        if SIGN_TEXTURE.search(Path(name).stem):
            updates[name] = raw
            continue
        try:
            image = Image.open(io.BytesIO(raw)).convert('RGBA')
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            image.save(out, 'PNG')
            updates[name] = out.getvalue()
        except (OSError, ValueError):
            updates[name] = raw
    model.rebuild_prefix(updates)


def validate_lod(path, reference, previous_triangles):
    model = Kn5(path)
    reference_textures = texture_payloads(reference)
    lod_textures = texture_payloads(model)
    for name, raw in reference_textures.items():
        if SIGN_TEXTURE.search(Path(name).stem) and lod_textures.get(name) != raw:
            raise ValueError('LOD changed a destination/display texture: ' + name)
    if dummy_pivots(model) != dummy_pivots(reference):
        raise ValueError('LOD moved or removed an animation pivot: ' + str(path))
    if np.max(abs(model_bounds(model) - model_bounds(reference))) > .15:
        raise ValueError('LOD changed overall silhouette bounds: ' + str(path))
    textures = {t['name'] for t in model.textures}
    for material in model.materials:
        if any(m['texture'] not in textures for m in material['maps']):
            raise ValueError('LOD has a missing texture: ' + str(path))
    for _, node in model.root.walk():
        if node.kind not in (2, 3):
            continue
        offset = node.vertex_offset + node.vertex_count * node.vertex_stride
        indices = np.frombuffer(node.payload, '<u2', node.index_count, offset + 4)
        if not len(indices) or len(indices) % 3 or indices.max() >= node.vertex_count or not np.isfinite(node.vertices).all():
            raise ValueError('LOD has invalid geometry: ' + node.name)
    triangles = triangle_count(model)
    if not 0 < triangles < previous_triangles:
        raise ValueError('LOD is not progressively simpler: ' + str(path))
    # Text/sign planes keep their original vertices and UVs.
    source_signs = [(n.name, bytes(n.payload)) for _, n in reference.root.walk()
                    if n.kind == 2 and re.search(r'destination|hanover|gorba|display', n.name, re.I)]
    signs = [(n.name, bytes(n.payload)) for _, n in model.root.walk()
             if n.kind == 2 and re.search(r'destination|hanover|gorba|display', n.name, re.I)]
    if signs != source_signs:
        raise ValueError('LOD changed a destination screen: ' + str(path))
    return triangles


def create_chain(source, output, stem, module=MODULE, reuse=False):
    if not module.is_file():
        raise FileNotFoundError('Install meshoptimizer@1.3.0 into outputs/KMB_20MB/deps or pass --meshoptimizer')
    output.mkdir(parents=True, exist_ok=True)
    cached = [output / f'{stem}_lod{level}.kn5' for level in range(1, 5)]
    manifest_path = output / f'{stem}_lod_manifest.json'
    def digest_source():
        digest = hashlib.sha256(source.prefix)
        for _, node in source.root.walk():
            digest.update(node.name.encode('utf-8'))
            digest.update(node.payload)
        return digest.hexdigest()
    signature = {'source': digest_source(),
                 'builder': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 'simplifier': hashlib.sha256((ROOT / 'tools/simplify_kmb_lods.mjs').read_bytes()).hexdigest(),
                 'meshoptimizer': hashlib.sha256(module.read_bytes()).hexdigest(),
                 'ratios': [list(x) for x in RATIOS], 'levels': [512, 256, 128, 64]}
    if reuse and all(p.is_file() for p in cached):
        if not manifest_path.is_file() or json.loads(manifest_path.read_text(encoding='utf-8')).get('signature') != signature:
            raise ValueError('Staged LODs were built from different source or settings; make a fresh build')
        file_hashes = {x['name']: x['sha256'] for x in json.loads(manifest_path.read_text(encoding='utf-8'))['files']}
        if any(hashlib.sha256(path.read_bytes()).hexdigest() != file_hashes.get(path.name) for path in cached):
            raise ValueError('A staged LOD file changed; make a fresh build')
        previous = triangle_count(source)
        levels = []
        for level, path in enumerate(cached, 1):
            previous = validate_lod(path, source, previous)
            levels.append({'level': level, 'file': path.name, 'triangles': previous,
                           'bytes': path.stat().st_size, 'revalidated': True,
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        return levels
    model = copy.deepcopy(source)
    previous = triangle_count(source)
    levels = []
    for level, cap in enumerate((512, 256, 128, 64), 1):
        details = simplify_level(model, level, output / 'mesh_work' / stem / str(level), module)
        reduce_textures(model, cap)
        path = output / f'{stem}_lod{level}.kn5'
        model.write(path)
        previous = validate_lod(path, source, previous)
        levels.append({'level': level, 'file': path.name, 'triangles': previous,
                       'bytes': path.stat().st_size, 'texture_cap': cap, **details,
                       'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest_path.write_text(json.dumps({'signature': signature, 'files': [
        {'name': x['file'], 'sha256': x['sha256']} for x in levels]}, indent=2), encoding='utf-8')
    return levels


def native_config(car_id):
    sections = ['[COCKPIT_HR]\nDISTANCE_SWITCH=0\n']
    for level in range(5):
        name = f'{car_id}.kn5' if level == 0 else f'{car_id}_lod{level}.kn5'
        sections.append(f'[LOD_{level}]\nFILE={name}\nIN={NATIVE_BANDS[level]}\nOUT={NATIVE_BANDS[level+1]}\n')
    return '\n'.join(sections)


def ensure_closed():
    procs = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq acs.exe', '/FO', 'CSV'], capture_output=True, text=True, check=True)
    if '"acs.exe"' in procs.stdout.lower():
        raise RuntimeError('Close Assetto Corsa before installing bus LODs')


def install_planner_switching(tool, backup):
    """Patch only this known Planner's LOD update; leave stock definitions alone."""
    path = tool / 'src/simulation/TrafficCar.lua'
    source = path.read_text(encoding='utf-8')
    marker = '-- KMB_DISTANCE_LODS_V1'
    if marker not in source:
        anchor = "local Pool = require('Pool')"
        if source.count(anchor) != 1:
            raise ValueError('Unknown TrafficCar.lua version; LOD patch not installed')
        source = source.replace(anchor, anchor + "\nlocal KmbBusLODs = require('KmbBusLODs')\n" + marker)
        anchor = '  if self._distanceSquared < 200^2 ~= (self._fakeShadow ~= nil) then'
        if source.count(anchor) != 1:
            raise ValueError('Unknown Planner updateLODs method; LOD patch not installed')
        source = source.replace(anchor, '  KmbBusLODs.update(self)\n\n' + anchor)
    from luaparser import ast
    module = (ROOT / 'tools/kmb_traffic_lods.lua').read_text(encoding='utf-8')
    ast.parse(source)
    ast.parse(module)
    write_backed_up(tool / 'src/simulation/KmbBusLODs.lua', module.encode('utf-8'), backup)
    write_backed_up(path, source.encode('utf-8'), backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ac', type=Path, default=AC)
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/KMB_LODS')
    parser.add_argument('--meshoptimizer', type=Path, default=MODULE)
    parser.add_argument('--only', choices=[b['id'] for b in buses()])
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--resume', type=Path, help='Reuse and revalidate a previously staged run')
    args = parser.parse_args()
    if args.install:
        ensure_closed()
    run = args.resume if args.resume else args.output / datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    results = []
    for bus in buses():
        if args.only and bus['id'] != args.only:
            continue
        car = args.ac / 'content/cars' / bus['id']
        main_path = car / (car.name + '.kn5')
        source_digest = hashlib.sha256(main_path.read_bytes()).hexdigest()
        source = Kn5(main_path)
        dest = run / car.name
        levels = create_chain(source, dest, car.name, args.meshoptimizer, reuse=args.resume is not None)
        (dest / 'lods.ini').write_text(native_config(car.name), encoding='utf-8')
        result = {'car': car.name, 'status': 'PASS', 'main_triangles': triangle_count(source),
                  'main_sha256': source_digest, 'levels': levels}
        if args.install:
            ensure_closed()
            backup = run / 'backups' / car.name
            for item in levels:
                write_backed_up(car / item['file'], (dest / item['file']).read_bytes(), backup)
            # Switch only after every required model is in place.
            write_backed_up(car / 'data/lods.ini', (dest / 'lods.ini').read_bytes(), backup)
            previous = triangle_count(source)
            config = ini(car / 'data/lods.ini')
            for level, item in enumerate(levels, 1):
                if config[f'LOD_{level}']['FILE'] != item['file']:
                    raise ValueError('Installed LOD reference mismatch')
                path = car / item['file']
                if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                    raise ValueError('Installed LOD hash mismatch')
                previous = validate_lod(path, source, previous)
            if hashlib.sha256(main_path.read_bytes()).hexdigest() != source_digest:
                raise ValueError('Main car model unexpectedly changed')
        results.append(result)
        print(json.dumps(result), flush=True)
    run.mkdir(parents=True, exist_ok=True)
    report = {'status': 'PASS', 'installed': args.install, 'buses': results,
              'bands_m': NATIVE_BANDS, 'runtime': 'pending user AC test'}
    (run / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Report: ' + str(run / 'validation.json'), flush=True)


if __name__ == '__main__':
    main()
