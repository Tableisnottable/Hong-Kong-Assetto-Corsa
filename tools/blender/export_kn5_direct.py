"""Export Blender meshes directly to Assetto Corsa KN5 format (no ksEditor needed).

KN5 format: "sc6969" header, embedded textures, materials, recursive node tree.
Based on TerraLap export_kn5.py (MIT) and RaduMC/kn5-converter format spec.

Usage (from repo root):
    blender --background --python tools/blender/export_kn5_direct.py -- content/cars/hk_cat1_toyota_yaris/body.fbx content/cars/hk_cat1_toyota_yaris/hk_cat1_toyota_yaris.kn5
    blender --background --python tools/blender/export_kn5_direct.py -- build/HP1C/tin_kwong_road/hd_map.fbx content/tracks/hong_kong_1to1/hd_map.kn5
"""

from __future__ import annotations

import os
import struct
import sys
import zlib

MAX_KN5_VERTICES = 65_535


def write_string(f, s):
    data = s.encode("utf-8")
    f.write(struct.pack("<i", len(data)))
    f.write(data)


def write_header(f, version=6):
    f.write(b"sc6969")
    f.write(struct.pack("<i", version))
    if version > 5:
        f.write(struct.pack("<i", 0))  # v6 extra field


def write_textures(f, textures):
    """textures = list of (name, dds/png_bytes)."""
    f.write(struct.pack("<i", len(textures)))
    for name, tex_data in textures:
        f.write(struct.pack("<i", 1))  # 1 = embedded
        write_string(f, name)
        f.write(struct.pack("<i", len(tex_data)))
        f.write(tex_data)


def write_materials(f, materials, version=6):
    f.write(struct.pack("<i", len(materials)))
    for mat in materials:
        write_string(f, mat["name"])
        write_string(f, mat["shader"])
        # alpha_blend, alpha_test flags
        f.write(struct.pack("<B", 0))
        f.write(struct.pack("<B", 0))
        if version > 4:
            f.write(struct.pack("<i", 0))
        props = mat.get("properties", {})
        f.write(struct.pack("<i", len(props)))
        for pname, pvalue in props.items():
            write_string(f, pname)
            f.write(struct.pack("<f", pvalue))
            f.write(b"\x00" * 36)
        samplers = mat.get("samplers", [])
        f.write(struct.pack("<i", len(samplers)))
        for sname, slot, tname in samplers:
            write_string(f, sname)
            f.write(struct.pack("<i", slot))
            write_string(f, tname)


def write_dummy_node(f, name, matrix, children_count):
    """Type 1 (Dummy) node header + 4x4 transform."""
    f.write(struct.pack("<i", 1))
    write_string(f, name)
    children_offset = f.tell()
    f.write(struct.pack("<i", children_count))
    f.write(struct.pack("<B", 1))
    for row in range(4):
        for col in range(4):
            f.write(struct.pack("<f", matrix[row][col]))
    return children_offset


def compute_bounding_sphere(vertices):
    if not vertices:
        return (0.0, 0.0, 0.0, 0.0)
    positions = [v[0] for v in vertices]
    min_x = min(p[0] for p in positions)
    max_x = max(p[0] for p in positions)
    min_y = min(p[1] for p in positions)
    max_y = max(p[1] for p in positions)
    min_z = min(p[2] for p in positions)
    max_z = max(p[2] for p in positions)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    cz = (min_z + max_z) / 2.0
    radius = max(
        ((p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2) ** 0.5
        for p in positions
    )
    return (cx, cy, cz, radius)


def write_mesh_node(f, name, vertices, indices, material_id, *, visible=True):
    """Type 2 (Mesh) node with no children."""
    if len(vertices) > MAX_KN5_VERTICES:
        raise ValueError(f"mesh {name} has {len(vertices)} vertices; limit 65535")
    if len(indices) % 3:
        raise ValueError(f"mesh {name} has non-triangular indices")
    f.write(struct.pack("<i", 2))
    write_string(f, name)
    f.write(struct.pack("<i", 0))  # children count
    f.write(struct.pack("<B", 1))
    f.write(struct.pack("<3B", 1, int(visible), 0))
    f.write(struct.pack("<i", len(vertices)))
    for pos, normal, uv, tangent in vertices:
        f.write(struct.pack("<3f3f2f3f", *pos, *normal, *uv, *tangent))
    f.write(struct.pack("<i", len(indices)))
    for i in range(0, len(indices), 3):
        f.write(struct.pack("<3H", indices[i], indices[i + 1], indices[i + 2]))
    f.write(struct.pack("<i", material_id))
    cx, cy, cz, radius = compute_bounding_sphere(vertices)
    f.write(struct.pack("<i", 0))
    f.write(struct.pack("<f", 0.0))
    f.write(struct.pack("<f", 0.0))
    f.write(struct.pack("<3f", cx, cy, cz))
    f.write(struct.pack("<f", radius))
    f.write(struct.pack("<B", 1))


def solid_png(red, green, blue, alpha=255):
    """1x1 RGBA PNG."""
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixels = zlib.compress(bytes((0, red, green, blue, alpha)))
    return signature + chunk(b"IHDR", header) + chunk(b"IDAT", pixels) + chunk(b"IEND", b"")


def identity_matrix():
    return [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def obj_to_matrix(obj):
    """Blender world matrix -> KN5 row-major (Z-up to Y-up)."""
    m = obj.matrix_world
    r = [[m[row][col] for col in range(4)] for row in range(4)]
    return [
        [r[0][0], r[2][0], -r[1][0], r[3][0]],
        [r[0][2], r[2][2], -r[1][2], r[3][2]],
        [-r[0][1], -r[2][1], r[1][1], -r[3][1]],
        [r[0][3], r[2][3], -r[1][3], r[3][3]],
    ]


def extract_mesh_data(obj, mat_name_to_id):
    """Extract vertices/indices from a Blender mesh object with AC coordinate conversion."""
    import bpy

    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        mesh.calc_loop_triangles()
        if mesh.uv_layers:
            try:
                mesh.calc_tangents()
            except Exception:
                pass

        world_mat = obj.matrix_world
        tangent_mat = world_mat.to_3x3()
        normal_mat = tangent_mat.inverted_safe().transposed()

        uv_layer = mesh.uv_layers.active
        corner_normals = mesh.corner_normals

        vertices = []
        indices = []
        index_map = {}

        material_id = 0
        if mesh.materials and mesh.materials[0] is not None:
            material_id = mat_name_to_id.get(mesh.materials[0].name, 0)

        for loop_triangle in mesh.loop_triangles:
            tri = []
            for loop_index in loop_triangle.loops:
                loop = mesh.loops[loop_index]
                vertex = mesh.vertices[loop.vertex_index]

                coordinate = world_mat @ vertex.co
                position = (
                    round(coordinate.x, 6),
                    round(coordinate.z, 6),
                    round(-coordinate.y, 6),
                )
                transformed_normal = normal_mat @ corner_normals[loop_index].vector
                transformed_normal.normalize()
                normal = (
                    round(transformed_normal.x, 6),
                    round(transformed_normal.z, 6),
                    round(-transformed_normal.y, 6),
                )
                if uv_layer:
                    raw_uv = uv_layer.data[loop_index].uv
                    uv = (round(raw_uv[0], 6), round(1.0 - raw_uv[1], 6))
                else:
                    uv = (0.0, 0.0)
                try:
                    transformed_tangent = tangent_mat @ loop.tangent
                    transformed_tangent.normalize()
                    tangent = (
                        round(transformed_tangent.x, 6),
                        round(transformed_tangent.z, 6),
                        round(-transformed_tangent.y, 6),
                    )
                except Exception:
                    tangent = (1.0, 0.0, 0.0)

                key = (position, normal, uv)
                if key not in index_map:
                    index_map[key] = len(vertices)
                    vertices.append((position, normal, uv, tangent))
                tri.append(index_map[key])
            indices.extend(tri)
        return vertices, indices, material_id
    finally:
        obj_eval.to_mesh_clear()


def main():
    args = sys.argv
    if "--" in args:
        idx = args.index("--")
        remaining = args[idx + 1 :]
    else:
        remaining = args[1:]
    if len(remaining) < 2:
        print("Usage: blender --background --python export_kn5_direct.py -- <input.fbx> <output.kn5>")
        sys.exit(1)

    fbx_path = os.path.abspath(remaining[0])
    kn5_path = os.path.abspath(remaining[1])

    import bpy

    # Clear scene and import FBX
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=fbx_path)
    print(f"Imported {fbx_path}")

    mesh_objects = [o for o in bpy.data.objects if o.type == "MESH"]
    empty_objects = [o for o in bpy.data.objects if o.type == "EMPTY"]
    mesh_objects.sort(key=lambda o: o.name)
    print(f"  Meshes: {len(mesh_objects)}, Empties: {len(empty_objects)}")

    # Build materials
    materials_list = []
    mat_name_to_id = {}
    textures = []
    seen_tex = set()

    # Default material for objects without one
    default_mat = bpy.data.materials.new("HK_BODY")
    default_mat.diffuse_color = (0.8, 0.1, 0.1, 1.0)  # red
    if not any(o.data.materials for o in mesh_objects):
        for mesh_obj in mesh_objects:
            mesh_obj.data.materials.append(default_mat)

    for mat in bpy.data.materials:
        if mat is None:
            continue
        name = mat.name
        if name in mat_name_to_id:
            continue
        # check if any mesh uses this material
        used = any(
            mat.name in [m.name for m in o.data.materials if m]
            for o in mesh_objects
        )
        if not used:
            continue
        tex_name = f"{name.lower().replace(' ', '_')}.png"
        # Use diffuse color (works with or without nodes)
        try:
            color = tuple(max(0, min(255, round(c * 255))) for c in mat.diffuse_color)
        except Exception:
            color = (200, 200, 200, 255)
        if tex_name not in seen_tex:
            seen_tex.add(tex_name)
            textures.append((tex_name, solid_png(color[0], color[1], color[2], color[3])))
        mat_id = len(materials_list)
        mat_name_to_id[name] = mat_id
        materials_list.append({
            "name": name,
            "shader": "ksPerPixel",
            "properties": {
                "ksAmbient": 0.5,
                "ksDiffuse": 0.7,
                "ksSpecular": 0.2,
                "ksSpecularEXP": 15.0,
            },
            "samplers": [("txDiffuse", 0, tex_name)],
        })
        print(f"  Material: {name} -> {tex_name}")

    # Write KN5
    print(f"Writing {kn5_path}...")
    with open(kn5_path, "wb") as f:
        write_header(f, version=6)
        write_textures(f, textures)
        write_materials(f, materials_list, version=6)

        root_children_offset = write_dummy_node(f, "HK_ROOT", identity_matrix(), 0)
        root_children = 0

        for obj in mesh_objects:
            vertices, indices, mat_id = extract_mesh_data(obj, mat_name_to_id)
            if not vertices or not indices:
                print(f"  [skip] {obj.name}: no geometry")
                continue
            # Split into 65535-vertex chunks if needed
            if len(vertices) > MAX_KN5_VERTICES:
                # simple split by vertex budget
                chunks = []
                current_v = []
                current_i = []
                vmap = {}
                for tri_i in range(0, len(indices), 3):
                    tri = indices[tri_i : tri_i + 3]
                    local = []
                    for vi in tri:
                        if vi not in vmap:
                            vmap[vi] = len(current_v)
                            current_v.append(vertices[vi])
                        local.append(vmap[vi])
                    current_i.extend(local)
                    if len(current_v) > MAX_KN5_VERTICES - 100:
                        chunks.append((current_v, current_i))
                        current_v, current_i, vmap = [], [], {}
                if current_v:
                    chunks.append((current_v, current_i))
                for ci, (cv, ci_inds) in enumerate(chunks):
                    node_name = f"{obj.name}_{ci:03d}" if ci else obj.name
                    write_mesh_node(f, node_name, cv, ci_inds, mat_id)
                    root_children += 1
                    print(f"  Mesh: {node_name} ({len(cv)} verts, {len(ci_inds)} idx)")
            else:
                write_mesh_node(f, obj.name, vertices, indices, mat_id)
                root_children += 1
                print(f"  Mesh: {obj.name} ({len(vertices)} verts, {len(indices)} idx)")

        end_offset = f.tell()
        f.seek(root_children_offset)
        f.write(struct.pack("<i", root_children))
        f.seek(end_offset)

    size = os.path.getsize(kn5_path)
    print(f"[DONE] {kn5_path} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
