# -*- coding: utf-8 -*-
"""Structural validator for KN5 files produced by export_kn5_direct.py.

Parses header, embedded textures, materials and the full node tree, then
reports problems that would make Assetto Corsa reject or misrender a model:

  * bad magic / unsupported version
  * truncated textures / materials / nodes
  * mesh with no vertices, non-triangular indices, or an out-of-range
    material index
  * missing AC control nodes for tracks (AC_START / AC_PIT / AC_TIME)
  * vertex/index counts beyond the 65535 limit

Usage:
    python tools/validate_kn5.py <file.kn5> [...]
    python tools/validate_kn5.py --tracks
    python tools/validate_kn5.py --cars
"""

import struct
import sys
from pathlib import Path

AC_ROOT = Path(r"A:\SteamLibrary\steamapps\common\assettocorsa")
TRACK_REQUIRED = ("AC_START_0", "AC_PIT_0", "AC_TIME_0_L")


class Kn5Error(Exception):
    pass


class Reader:
    def __init__(self, data: bytes, path: Path):
        self.data = data
        self.off = 0
        self.path = path

    def need(self, n: int) -> None:
        if self.off + n > len(self.data):
            raise Kn5Error(
                f"truncated at {self.off}: need {n} bytes, "
                f"only {len(self.data) - self.off} left"
            )

    def i32(self) -> int:
        self.need(4)
        v = struct.unpack_from("<i", self.data, self.off)[0]
        self.off += 4
        return v

    def i16(self) -> int:
        self.need(2)
        v = struct.unpack_from("<H", self.data, self.off)[0]
        self.off += 2
        return v

    def byte(self) -> int:
        self.need(1)
        v = self.data[self.off]
        self.off += 1
        return v

    def raw(self, n: int) -> bytes:
        self.need(n)
        v = self.data[self.off : self.off + n]
        self.off += n
        return v

    def string(self) -> str:
        n = self.i32()
        if n < 0 or n > 4096:
            raise Kn5Error(f"implausible string length {n} at {self.off}")
        return self.raw(n).decode("utf-8", "replace")

    def skip_floats(self, n: int) -> None:
        self.raw(4 * n)


def parse(path: Path) -> dict:
    data = path.read_bytes()
    r = Reader(data, path)

    magic = r.raw(6)
    if magic != b"sc6969":
        raise Kn5Error(f"bad magic {magic!r}")
    version = r.i32()
    if version not in (5, 6):
        raise Kn5Error(f"unsupported version {version}")
    if version > 5:
        extra = r.i32()
        if extra != 0:
            raise Kn5Error(f"unexpected v6 extra field {extra}")

    textures = []
    for _ in range(r.i32()):
        tex_type = r.i32()
        if tex_type == 0:
            # type 0 entries carry no name, no size and no blob (marker only)
            textures.append((0, "", 0))
            continue
        name = r.string()
        size = r.i32()
        r.raw(size)
        textures.append((tex_type, name, size))

    materials = []
    for _ in range(r.i32()):
        mat = {
            "name": r.string(),
            "shader": r.string(),
            "blend": r.byte(),
            "alpha_tested": r.byte(),
        }
        r.i32()  # unknown/reserved
        props = {}
        for _ in range(r.i32()):
            k = r.string()
            props[k] = struct.unpack_from("<f", data, r.off)[0]
            r.raw(4 + 36)
        samplers = []
        for _ in range(r.i32()):
            sname = r.string()
            slot = r.i32()
            tname = r.string()
            samplers.append((sname, slot, tname))
        mat["samplers"] = samplers
        materials.append(mat)

    node_names = []
    meshes = []
    issues = []

    def read_node(depth=0):
        if depth > 64:
            raise Kn5Error("node nesting deeper than 64")
        node_type = r.i32()
        name = r.string()
        node_names.append(name)
        if node_type == 1:  # dummy
            children = r.i32()
            r.skip_floats(16)
            for _ in range(children):
                read_node(depth + 1)
        elif node_type == 2:  # mesh
            children = r.i32()
            r.byte()   # cast_shadows
            visible = r.byte()   # is_visible
            r.byte()   # is_transparent
            nv = r.i32()
            if nv < 0 or nv > 65535:
                issues.append(f"mesh {name}: vertex count {nv} invalid")
            r.skip_floats(nv * 11)
            ni = r.i32()
            if ni < 0 or ni % 3:
                issues.append(f"mesh {name}: index count {ni} not a triangle list")
            r.raw(ni * 2)
            mat_id = r.i32()
            if mat_id < 0 or mat_id >= len(materials):
                issues.append(f"mesh {name}: material index {mat_id} out of range")
            r.i32()            # unknown
            r.skip_floats(4)   # padding, centre xyz
            r.skip_floats(2)   # radius + trailing padding
            if nv == 0 or ni == 0:
                issues.append(f"mesh {name}: empty geometry")
            meshes.append({"name": name, "verts": nv, "indices": ni, "visible": visible})
            for _ in range(children):
                read_node(depth + 1)
        else:
            raise Kn5Error(f"unknown node type {node_type} at offset {r.off - 4}")

    try:
        read_node()
    except Kn5Error as exc:
        raise Kn5Error(f"{exc} (root node)") from None

    trailing = len(data) - r.off
    if trailing > 0:
        issues.append(f"{trailing} unparsed trailing bytes")

    return {
        "path": path,
        "size": len(data),
        "version": version,
        "textures": textures,
        "materials": materials,
        "nodes": node_names,
        "meshes": meshes,
        "issues": issues,
    }


def report(path: Path, *, require_controls: bool = False) -> bool:
    try:
        info = parse(path)
    except (Kn5Error, struct.error) as exc:
        print(f"[FAIL] {path.name}: {exc}")
        return False

    issues = list(info["issues"])
    if require_controls:
        for node in TRACK_REQUIRED:
            if node not in info["nodes"]:
                issues.append(f"missing required node {node}")

    total_v = sum(m["verts"] for m in info["meshes"])
    total_i = sum(m["indices"] for m in info["meshes"])
    if issues:
        print(f"[FAIL] {path.name} ({info['size']/1024/1024:.1f} MB)")
        for i in issues[:12]:
            print(f"        - {i}")
        return False

    print(
        f"[PASS] {path.name}: v{info['version']}, "
        f"{len(info['textures'])} textures, {len(info['materials'])} materials, "
        f"{len(info['meshes'])} meshes, {total_v:,} verts, {total_i:,} tris, "
        f"{info['size']/1024/1024:.1f} MB"
    )
    return True


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    if args[0] == "--tracks":
        files = sorted((AC_ROOT / "content" / "tracks").glob("hong_kong_1to1*/hd_map.kn5"))
        ok = sum(report(f, require_controls=True) for f in files)
        print(f"\n{ok}/{len(files)} tracks valid")
        sys.exit(0 if ok == len(files) else 1)

    if args[0] == "--cars":
        files = []
        for car in sorted((AC_ROOT / "content" / "cars").glob("hk_cat*")):
            files.append(car / f"{car.name}.kn5")
            files.append(car / "collider.kn5")
        ok = sum(report(f) for f in files if f.exists())
        print(f"\n{ok}/{len(files)} car models valid")
        sys.exit(0 if ok == len(files) else 1)

    ok = sum(report(Path(a)) for a in args)
    print(f"\n{ok}/{len(args)} files valid")
    sys.exit(0 if ok == len(args) else 1)


if __name__ == "__main__":
    main()
