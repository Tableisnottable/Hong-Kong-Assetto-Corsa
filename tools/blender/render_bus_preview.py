"""Render actual installed KN5 geometry/skin artwork; called by generate_bus_previews.py."""
import argparse
import io
from pathlib import Path
import sys

import bpy
from mathutils import Vector
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kn5_tools import Kn5, read_u32, read_string


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("car", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("skins", nargs="+")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    car, out = args.car.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    model = Kn5(car / (car.name + ".kn5"))
    texdir = out / "textures"
    texdir.mkdir(exist_ok=True)
    embedded = io.BytesIO(model.prefix)
    embedded.seek(6)
    if read_u32(embedded) > 5:
        read_u32(embedded)
    for _ in range(read_u32(embedded)):
        read_u32(embedded)
        name = read_string(embedded)
        data = embedded.read(read_u32(embedded))
        (texdir / Path(name).name).write_bytes(data)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 6
    scene.render.resolution_x, scene.render.resolution_y = 1024, 576
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    texture_nodes, materials = [], []
    for data in model.materials:
        material = bpy.data.materials.new(data["name"])
        material.use_nodes = True
        material.use_backface_culling = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Roughness"].default_value = .6
        shader.inputs["Specular IOR Level"].default_value = .25
        texture = next((x["texture"] for x in data["maps"] if x["name"] == "txDiffuse"), None)
        if texture and (texdir / Path(texture).name).exists():
            image = material.node_tree.nodes.new("ShaderNodeTexImage")
            texture_nodes.append((texture, image))
            material.node_tree.links.new(image.outputs["Color"], shader.inputs["Base Color"])
            if data["blend"] or data["alpha_test"]:
                material.node_tree.links.new(image.outputs["Alpha"], shader.inputs["Alpha"])
                material.surface_render_method = "DITHERED"
            emissive = data["props"].get("ksEmissive", (0,) * 10)
            if max(emissive) > 0:
                material.node_tree.links.new(image.outputs["Color"], shader.inputs["Emission Color"])
                shader.inputs["Emission Strength"].default_value = max(emissive[3:6]) or emissive[0]
        materials.append(material)

    def to_blender(vertices):
        return np.asarray(vertices)[:, [0, 2, 1]] * np.array([-1., 1., 1.])

    samples = []

    def visit(node, parent=np.eye(4), active=True):
        active = active and node.active
        world = node.matrix @ parent if node.kind == 1 else parent
        if node.kind == 2 and active and node.vertex_count:
            v = node.vertices
            points = to_blender(v[:, :3] @ world[:3, :3] + world[3, :3])
            samples.append(points)
            indices = np.frombuffer(node.payload, dtype="<u2", count=node.index_count,
                offset=node.vertex_offset + node.vertex_count * node.vertex_stride + 4).reshape(-1, 3)
            mesh = bpy.data.meshes.new(node.name)
            mesh.from_pydata(points.tolist(), [], indices.tolist())
            mesh.update()
            mesh.materials.append(materials[node.material_id])
            mesh.polygons.foreach_set("use_smooth", [True] * len(indices))
            uv = mesh.uv_layers.new(name="UVMap")
            coords = v[:, 6:8][indices.flatten()].copy()
            coords[:, 1] = 1 - coords[:, 1]
            uv.data.foreach_set("uv", coords.flatten())
            # Preserve native KN5 normals; geometry-derived normals suffice for
            # previews and avoid a Blender crash on degenerate OMSI faces.
            obj = bpy.data.objects.new(node.name, mesh)
            scene.collection.objects.link(obj)
        for child in node.children:
            visit(child, world, active)

    visit(model.root)
    points = np.concatenate(samples)
    low, high = points.min(0), points.max(0)
    center = Vector(((low + high) / 2).tolist())
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, float(low[2]) - .02))
    floor = bpy.context.object
    material = bpy.data.materials.new("Preview floor")
    material.diffuse_color = (.18, .19, .21, 1)
    floor.data.materials.append(material)
    world = bpy.data.worlds.new("Preview studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (.65, .72, .82, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = .8
    scene.world = world
    for offset, energy, size in [((5, 8, 10), 1800, 8), ((-8, 1, 6), 1400, 9), ((3, -8, 6), 1800, 7)]:
        light = bpy.data.lights.new("Studio softbox", "AREA")
        light.energy, light.size = energy, size
        obj = bpy.data.objects.new(light.name, light)
        scene.collection.objects.link(obj)
        obj.location = center + Vector(offset)
        obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()
    camera_data = bpy.data.cameras.new("Bus preview")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = float(max(high - low)) * 1.20
    camera_data.clip_start, camera_data.clip_end = .03, 1000
    camera.location = center + Vector((12, 16, 7))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    for skin in args.skins:
        images = {}
        for name, texture in texture_nodes:
            override = car / "skins" / skin / Path(name).name
            path = override if override.exists() else texdir / Path(name).name
            key = str(path)
            if key not in images:
                images[key] = bpy.data.images.load(key, check_existing=True)
            texture.image = images[key]
        skin_out = out / skin
        skin_out.mkdir(exist_ok=True)
        scene.render.filepath = str(skin_out / "preview.png")
        bpy.ops.render.render(write_still=True)
        print("BUS_PREVIEW_SAVED " + scene.render.filepath, flush=True)


if __name__ == "__main__":
    main()
