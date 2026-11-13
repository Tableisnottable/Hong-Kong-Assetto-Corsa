"""Small lossless KN5 reader/editor. Format checked against AcTools Kn5Reader/Writer.

Textures, material definitions, and mesh data remain byte-for-byte intact unless
explicitly edited. Used only for the separate E6M playable prototype.
"""
import io
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


def read_u32(f):
    return struct.unpack('<I', f.read(4))[0]


def read_string(f):
    n = read_u32(f)
    if n > 1000000:
        raise ValueError('Implausible KN5 string length')
    return f.read(n).decode('utf-8', errors='strict')


def string_bytes(value):
    b = value.encode('utf-8')
    return struct.pack('<I', len(b)) + b


@dataclass
class Node:
    kind: int
    name: str
    active: bool
    payload: bytearray
    children: list = field(default_factory=list)
    vertex_count: int = 0
    vertex_offset: int = 0
    vertex_stride: int = 44
    index_count: int = 0
    material_id: int = -1

    @property
    def matrix(self):
        return np.frombuffer(self.payload, dtype='<f4', count=16).reshape(4, 4).copy() if self.kind == 1 else np.eye(4)

    @property
    def vertices(self):
        return np.ndarray((self.vertex_count, self.vertex_stride // 4), dtype='<f4', buffer=self.payload, offset=self.vertex_offset)

    @classmethod
    def dummy(cls, name, children=None, translation=(0, 0, 0)):
        matrix = np.eye(4, dtype='<f4')
        matrix[3, :3] = translation
        return cls(1, name, True, bytearray(matrix.tobytes()), children or [])

    def walk(self, parent=''):
        yield parent, self
        for child in self.children:
            yield from child.walk(self.name)

    def write(self, f):
        f.write(struct.pack('<I', self.kind))
        f.write(string_bytes(self.name))
        f.write(struct.pack('<I?', len(self.children), self.active))
        f.write(self.payload)
        for child in self.children:
            child.write(f)


class Kn5:
    def __init__(self, path):
        data = Path(path).read_bytes()
        f = io.BytesIO(data)
        assert f.read(6) == b'sc6969'
        self.version = read_u32(f)
        if self.version > 5:
            self.extra = read_u32(f)
        self.textures = []
        for _ in range(read_u32(f)):
            active = read_u32(f)
            name = read_string(f)
            length = read_u32(f)
            f.seek(length, 1)
            self.textures.append({'name': name, 'bytes': length, 'active': active})
        self.materials = []
        for _ in range(read_u32(f)):
            name, shader = read_string(f), read_string(f)
            blend, alpha_test, depth = struct.unpack('<BBI', f.read(6))
            props = {}
            for _ in range(read_u32(f)):
                p_name = read_string(f)
                props[p_name] = struct.unpack('<10f', f.read(40))
            maps = []
            for _ in range(read_u32(f)):
                map_name, slot = read_string(f), read_u32(f)
                maps.append({'name': map_name, 'slot': slot, 'texture': read_string(f)})
            self.materials.append({'name': name, 'shader': shader, 'blend': blend, 'alpha_test': alpha_test, 'depth': depth, 'props': props, 'maps': maps})
        self.prefix = data[:f.tell()]

        def read_node():
            kind = read_u32(f)
            if kind not in (1, 2, 3):
                raise ValueError('Invalid node type: ' + str(kind))
            name = read_string(f)
            count = read_u32(f)
            active = bool(f.read(1)[0])
            start = f.tell()
            n = Node(kind, name, active, bytearray())
            if kind == 1:
                f.seek(64, 1)
            else:
                f.seek(3, 1)
                if kind == 3:
                    for _ in range(read_u32(f)):
                        read_string(f)
                        f.seek(64, 1)
                    n.vertex_stride = 76
                n.vertex_count = read_u32(f)
                n.vertex_offset = f.tell() - start
                f.seek(n.vertex_count * n.vertex_stride, 1)
                n.index_count = read_u32(f)
                f.seek(n.index_count * 2, 1)
                n.material_id = read_u32(f)
                f.seek(4 + (25 if kind == 2 else 8), 1)
            n.payload = bytearray(data[start:f.tell()])
            n.children = [read_node() for _ in range(count)]
            return n

        self.root = read_node()
        if f.tell() != len(data):
            raise ValueError(f'KN5 trailing data: {len(data) - f.tell()} bytes')

    def write(self, path):
        with open(path, 'wb') as f:
            f.write(self.prefix)
            self.root.write(f)

    def rebuild_prefix(self, updates=None):
        """Keep embedded texture bytes, update named textures/material records."""
        updates = updates or {}
        f = io.BytesIO(self.prefix)
        f.seek(6)
        version = read_u32(f)
        extra = read_u32(f) if version > 5 else None
        textures = []
        for _ in range(read_u32(f)):
            active, name = read_u32(f), read_string(f)
            data = f.read(read_u32(f))
            textures.append((active, name, updates.get(name, data)))
        names = {name for _, name, _ in textures}
        textures.extend((1, name, data) for name, data in updates.items() if name not in names)
        out = io.BytesIO()
        out.write(b'sc6969' + struct.pack('<I', version))
        if extra is not None:
            out.write(struct.pack('<I', extra))
        out.write(struct.pack('<I', len(textures)))
        for active, name, data in textures:
            out.write(struct.pack('<I', active) + string_bytes(name) + struct.pack('<I', len(data)) + data)
        out.write(struct.pack('<I', len(self.materials)))
        for m in self.materials:
            out.write(string_bytes(m['name']) + string_bytes(m['shader']))
            out.write(struct.pack('<BBI', m['blend'], m['alpha_test'], m['depth']))
            out.write(struct.pack('<I', len(m['props'])))
            for name, values in m['props'].items():
                out.write(string_bytes(name) + struct.pack('<10f', *values))
            out.write(struct.pack('<I', len(m['maps'])))
            for mapping in m['maps']:
                out.write(string_bytes(mapping['name']) + struct.pack('<I', mapping['slot']) + string_bytes(mapping['texture']))
        self.prefix = out.getvalue()

    def summary(self):
        return {'version': self.version, 'textures': len(self.textures), 'materials': len(self.materials), 'nodes': [
            {'parent': parent, 'name': n.name, 'kind': n.kind, 'active': n.active,
             **({'translation': n.matrix[3, :3].tolist()} if n.kind == 1 else {'vertices': n.vertex_count, 'triangles': n.index_count // 3, 'material': self.materials[n.material_id]['name']})}
            for parent, n in self.root.walk()]}


if __name__ == '__main__':
    model = Kn5(sys.argv[1])
    print(json.dumps(model.summary(), indent=2))
