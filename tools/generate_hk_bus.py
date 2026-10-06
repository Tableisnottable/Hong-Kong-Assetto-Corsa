from pathlib import Path
import math

OUT_DIR = Path(__file__).resolve().parents[1] / "asset" / "vehicles" / "hk_double_decker_bus"
OBJ_PATH = OUT_DIR / "hk_double_decker_bus.obj"
MTL_PATH = OUT_DIR / "hk_double_decker_bus.mtl"


class ObjBuilder:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.materials = []
        self.groups = []

    def add_box(self, center, size, material, group_name):
        cx, cy, cz = center
        sx, sy, sz = size
        hx = sx / 2.0
        hy = sy / 2.0
        hz = sz / 2.0

        base = len(self.vertices) + 1
        verts = [
            (cx - hx, cy - hy, cz - hz),
            (cx + hx, cy - hy, cz - hz),
            (cx + hx, cy + hy, cz - hz),
            (cx - hx, cy + hy, cz - hz),
            (cx - hx, cy - hy, cz + hz),
            (cx + hx, cy - hy, cz + hz),
            (cx + hx, cy + hy, cz + hz),
            (cx - hx, cy + hy, cz + hz),
        ]
        self.vertices.extend(verts)

        quads = [
            (0, 1, 2, 3),
            (4, 5, 6, 7),
            (0, 4, 7, 3),
            (1, 5, 6, 2),
            (3, 2, 6, 7),
            (0, 1, 5, 4),
        ]

        self.groups.append((group_name, material, [base + i for i in range(8)], quads))

    def add_cylinder(self, center, radius, height, material, group_name, segments=12):
        cx, cy, cz = center
        base = len(self.vertices) + 1
        ring_a = []
        ring_b = []
        for i in range(segments):
            angle = (2.0 * math.pi * i) / segments
            x = cx + radius * math.cos(angle)
            z = cz + radius * math.sin(angle)
            ring_a.append((x, cy - height / 2.0, z))
            ring_b.append((x, cy + height / 2.0, z))
        self.vertices.extend(ring_a)
        self.vertices.extend(ring_b)

        faces = []
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((base + i, base + j, base + segments + j, base + segments + i))

        # cap faces
        center_a = len(self.vertices) + 1
        center_b = len(self.vertices) + 2
        self.vertices.extend([(cx, cy - height / 2.0, cz), (cx, cy + height / 2.0, cz)])

        for i in range(segments):
            j = (i + 1) % segments
            faces.append((center_a, base + i, base + j))
            faces.append((center_b, base + segments + j, base + segments + i))

        self.groups.append((group_name, material, list(range(base, base + 2 * segments + 2)), faces))

    def write(self, obj_path, mtl_path):
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        with obj_path.open("w", encoding="utf-8") as f:
            f.write("# Hong Kong double-decker bus prototype\n")
            f.write("mtllib hk_double_decker_bus.mtl\n\n")
            for vx, vy, vz in self.vertices:
                f.write(f"v {vx:.6f} {vy:.6f} {vz:.6f}\n")

            for group_name, material, vertex_ids, faces in self.groups:
                f.write(f"g {group_name}\n")
                f.write(f"usemtl {material}\n")
                for face in faces:
                    if len(face) == 3:
                        a, b, c = face
                        f.write(f"f {a + 1} {b + 1} {c + 1}\n")
                    elif len(face) == 4:
                        a, b, c, d = face
                        f.write(f"f {a + 1} {b + 1} {c + 1} {d + 1}\n")
                f.write("\n")

        with mtl_path.open("w", encoding="utf-8") as f:
            f.write("# Materials for the Hong Kong double-decker bus prototype\n")
            f.write("newmtl bus_red\n")
            f.write("Ka 0.15 0.03 0.03\n")
            f.write("Kd 0.82 0.16 0.17\n")
            f.write("Ks 0.15 0.15 0.15\n")
            f.write("Ns 40.0\n\n")

            f.write("newmtl bus_window\n")
            f.write("Ka 0.05 0.08 0.10\n")
            f.write("Kd 0.18 0.22 0.30\n")
            f.write("Ks 0.25 0.25 0.25\n")
            f.write("Ns 80.0\n")
            f.write("d 0.85\n\n")

            f.write("newmtl bus_trim\n")
            f.write("Ka 0.05 0.05 0.05\n")
            f.write("Kd 0.10 0.10 0.12\n")
            f.write("Ks 0.20 0.20 0.20\n")
            f.write("Ns 30.0\n\n")

            f.write("newmtl bus_tire\n")
            f.write("Ka 0.03 0.03 0.03\n")
            f.write("Kd 0.05 0.05 0.05\n")
            f.write("Ks 0.08 0.08 0.08\n")
            f.write("Ns 8.0\n\n")

            f.write("newmtl bus_light\n")
            f.write("Ka 0.20 0.20 0.15\n")
            f.write("Kd 0.95 0.95 0.80\n")
            f.write("Ks 0.75 0.75 0.75\n")
            f.write("Ns 120.0\n")


def generate():
    mesh = ObjBuilder()

    # main lower deck body
    mesh.add_box((0.0, 1.65, 0.0), (10.6, 3.2, 2.55), "bus_red", "lower_deck")
    mesh.add_box((0.0, 3.85, 0.0), (9.6, 2.2, 2.35), "bus_red", "upper_deck")
    mesh.add_box((4.7, 4.3, 0.0), (0.8, 1.0, 2.2), "bus_trim", "front_cabin")

    # windows and deck glazing
    for x in (-3.3, -1.0, 1.3, 3.6):
        mesh.add_box((x, 3.1, 0.0), (1.3, 0.8, 2.15), "bus_window", f"window_{x}")
    for x in (-2.9, -0.4, 2.1):
        mesh.add_box((x, 5.2, 0.0), (1.5, 0.85, 2.12), "bus_window", f"upper_window_{x}")

    # front windshield and side glass
    mesh.add_box((5.15, 2.9, 0.0), (0.35, 1.0, 2.0), "bus_window", "windshield")
    mesh.add_box((-4.7, 1.75, 0.0), (0.35, 2.1, 2.2), "bus_window", "rear_glass")

    # front light bars
    mesh.add_box((5.35, 1.8, 0.8), (0.25, 0.2, 0.4), "bus_light", "front_light_left")
    mesh.add_box((5.35, 1.8, -0.8), (0.25, 0.2, 0.4), "bus_light", "front_light_right")

    # wheels
    wheel_x_positions = (-3.0, 3.0)
    wheel_z_positions = (-1.1, 1.1)
    for x in wheel_x_positions:
        for z in wheel_z_positions:
            mesh.add_cylinder((x, 0.45, z), 0.42, 0.45, "bus_tire", f"wheel_{x}_{z}", segments=12)

    mesh.write(OBJ_PATH, MTL_PATH)
    print(f"Created {OBJ_PATH}")
    print(f"Created {MTL_PATH}")


if __name__ == "__main__":
    generate()
