"""Regression checks for source mosaic alignment and protected extraction."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from PIL import Image

import prepare_full_loop_data as full
from collect_build_data import digest, selection
from prepare_collected_data import unpack
from prepare_regional_sources import clip_record, crop_terrain, portals
import numpy as np
from shapely.geometry import box
from audit_legacy_map_archives import inspect_header


class MapSourceTests(unittest.TestCase):
    def test_server_error_response_is_not_treated_as_model_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.zip"
            path.write_text('<html>Server error</html>')
            self.assertEqual(inspect_header(path), {"status": "INVALID_ZIP", "payload_kind": "html_response"})

    def test_unsafe_legacy_archive_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr('../model.fbx', 'invalid path')
            self.assertEqual(inspect_header(path), {"status": "UNSAFE_MEMBERS"})
    def tile(self, root, sheet, north, color):
        folder = root / "extracted" / f"tdop_{sheet}"
        folder.mkdir(parents=True)
        Image.new("RGB", (4, 4), color).save(folder / "photo.tif")
        (folder / "photo.tfw").write_text(f"0.25\n0\n0\n-0.25\n10.125\n{north - .125}\n")
        return {"role": "tdop", "folder": folder.relative_to(root).as_posix()}

    def fixture(self, root):
        (root / "index").mkdir()
        (root / "index/tdop_features.json").write_text(json.dumps({"features": [
            {"attributes": {"SHEETNO": s, "DATE_OF_PHOTOGRAPH": "3 Jan 2025"}} for s in ("N", "S")]}))
        out = root / "gis"
        out.mkdir()
        return out

    def test_two_sheets_preserve_north_south_and_pixel_centres(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = self.fixture(root)
            catalog = [self.tile(root, "N", 22, (220, 20, 20)),
                       self.tile(root, "S", 21, (20, 20, 220))]
            with patch.object(full, "ROOT", root):
                report = full.mosaic_orthophotos(root, catalog, [10, 20, 11, 22], out)
            self.assertEqual(report["dimensions_pixels"], [4, 8])
            self.assertEqual(report["pixel_centres_epsg2326_first"], [10.125, 21.875])
            self.assertEqual(report["uncovered_pixels"], 0)
            self.assertEqual(len(report["sources"]), 2)
            with Image.open(out / "full_loop_orthophoto.jpg") as image:
                self.assertGreater(image.getpixel((1, 1))[0], 200)
                self.assertGreater(image.getpixel((1, 6))[2], 200)
            world = list(map(float, (out / "full_loop_orthophoto.jgw").read_text().split()))
            self.assertEqual(world, [.25, 0, 0, -.25, 10.125, 21.875])

    def test_missing_sheet_refuses_black_padding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = self.fixture(root)
            catalog = [self.tile(root, "N", 22, (220, 20, 20))]
            with patch.object(full, "ROOT", root), self.assertRaisesRegex(ValueError, "uncovered pixels"):
                full.mosaic_orthophotos(root, catalog, [10, 20, 11, 22], out)
            self.assertFalse((out / "full_loop_orthophoto.jpg").exists())

    def test_overlapping_sheets_require_source_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = self.fixture(root)
            catalog = [self.tile(root, "N", 22, (220, 20, 20)),
                       self.tile(root, "S", 22, (20, 20, 220))]
            with patch.object(full, "ROOT", root), self.assertRaisesRegex(ValueError, "Overlapping"):
                full.mosaic_orthophotos(root, catalog, [10, 21, 11, 22], out)

    def test_modified_extracted_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "source.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("model.txt", "original")
            folder = unpack(path, root / "extracted", digest(path))
            (folder / "model.txt").write_text("hand edits")
            with self.assertRaisesRegex(ValueError, "Preserving modified"):
                unpack(path, folder, digest(path))
            self.assertEqual((folder / "model.txt").read_text(), "hand edits")

    def test_full_loop_bounds_include_retained_route_and_context(self):
        from collect_build_data import ROOT
        route = json.loads((ROOT / "driving_test/source/test_loop_source.json").read_text(encoding="utf-8"))
        west, south, east, north = selection("full-loop")[0]
        self.assertTrue(all(west <= e - 160 and e + 160 <= east and
                            south <= n - 160 and n + 160 <= north for e, n in route["xy"]))
        self.assertNotEqual(selection("pilot")[0], selection("full-loop")[0])

    def test_neighbouring_regions_share_portal_without_invented_osm_node(self):
        record = {"osm_id": 19, "xy": [[-2., 4.], [2., 4.]], "node_refs": [101, 102],
                  "grade_review_required": True}
        left = clip_record(record, box(-10, 0, 0, 10))[0]
        right = clip_record(record, box(0, 0, 10, 10))[0]
        self.assertEqual(left["node_refs"], [101, None])
        self.assertEqual(right["node_refs"], [None, 102])
        lp = portals(left, [-10, 0, 0, 10])[0]
        rp = portals(right, [0, 0, 10, 10])[0]
        self.assertEqual(lp["id"], rp["id"])
        self.assertEqual(lp["xy"], [0., 4.])
        self.assertIsNone(lp["source_node_ref"])
        self.assertTrue(lp["grade_review_required"])
        self.assertAlmostEqual(left["length_m"] + right["length_m"], 4.)

    def test_regional_terrain_preserves_grid_origin_and_nodata(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "terrain.npz"
            terrain = {"z": np.array([[1, 2, 3], [4, -9999, 6], [7, 8, 9]], dtype=np.float32),
                       "west_edge": 100., "north_edge": 230., "cell_m": 5., "nodata": -9999.}
            report = crop_terrain(terrain, [105., 215., 115., 225.], path)
            self.assertEqual(report, {"shape": [2, 2], "nodata_pixels": 1})
            with np.load(path) as crop:
                np.testing.assert_array_equal(crop["z"], [[-9999, 6], [8, 9]])
                self.assertEqual(float(crop["x_first_center"]), 107.5)
                self.assertEqual(float(crop["y_first_center"]), 222.5)


if __name__ == "__main__":
    unittest.main()
