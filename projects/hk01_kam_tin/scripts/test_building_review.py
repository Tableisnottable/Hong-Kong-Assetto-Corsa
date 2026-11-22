"""Coordinate and format regression tests for the separate building importer."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from prepare_building_review import local_resource, model_primitives, topology


class BuildingReviewTests(unittest.TestCase):
    def fixture(self, root):
        positions = np.array([[0, 0, 0], [2, 0, 0], [0, 0, 3]], dtype="<f4")
        colors = np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype="u1")
        indices = np.array([0, 1, 2], dtype="<u2")
        payload = positions.tobytes() + colors.tobytes() + b"\0" + indices.tobytes()
        (root / "geometry.bin").write_bytes(payload)
        document = {"asset": {"version": "2.0"}, "buffers": [{"uri": "geometry.bin", "byteLength": len(payload)}],
            "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36},
                            {"buffer": 0, "byteOffset": 36, "byteLength": 9},
                            {"buffer": 0, "byteOffset": 46, "byteLength": 6}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
                          {"bufferView": 1, "componentType": 5121, "count": 3, "type": "VEC3", "normalized": True},
                          {"bufferView": 2, "componentType": 5123, "count": 3, "type": "SCALAR"}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "COLOR_0": 1}, "indices": 2}]}],
            "nodes": [{"matrix": [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 825500, 9, -832500, 1], "children": [1]}, {"mesh": 0}],
            "scenes": [{"nodes": [0]}], "scene": 0}
        path = root / "building.gltf"
        path.write_text(json.dumps(document), encoding="utf-8")
        return path, document

    def test_vertex_colour_building_needs_no_uv_and_retains_native_height(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, _ = self.fixture(root)
            parts = list(model_primitives(path))
            self.assertEqual(len(parts), 1)
            part = parts[0]
            self.assertIsNone(part["uv"])
            self.assertIsNone(part["image"])
            np.testing.assert_allclose(part["vertices"], [[-500, -500, 9], [-498, -500, 9], [-500, -500, 12]])
            np.testing.assert_allclose(part["colors"], np.eye(3))

    def test_source_dependency_cannot_escape_model_folder(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for uri in ("../outside.bin", "https://example.com/model.bin", "data:application/octet-stream;base64,AAA"):
                with self.subTest(uri=uri), self.assertRaises(ValueError):
                    local_resource(root, uri)

    def test_bad_triangle_indices_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, document = self.fixture(root)
            payload = bytearray((root / "geometry.bin").read_bytes())
            payload[50:52] = (99).to_bytes(2, "little")
            (root / "geometry.bin").write_bytes(payload)
            with self.assertRaisesRegex(ValueError, "triangle indices"):
                list(model_primitives(path))

    def test_degenerate_face_removed_without_flattening_shape(self):
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 0, 4]], dtype=float)
        faces, report = topology(vertices, np.array([[0, 1, 2], [0, 0, 1]]))
        np.testing.assert_array_equal(faces, [[0, 1, 2]])
        self.assertEqual(report["degenerate_triangles_removed"], 1)
        self.assertFalse(report["flat_geometry"])
        self.assertEqual(report["extent_m"][2], 4.)


if __name__ == "__main__":
    unittest.main()
