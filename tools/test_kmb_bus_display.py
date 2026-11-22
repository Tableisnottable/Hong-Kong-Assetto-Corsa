"""Checks the complete HOF destination selector used by the six KMB buses."""
import tempfile
import unittest
from pathlib import Path

from prepare_kmb_displays import route_label
from set_kmb_bus_display import read_hof


class HofDisplayTests(unittest.TestCase):
    def test_reads_all_destinations_and_skips_trailing_version_record(self):
        contents = """[addterminus]
1001
51Y Tai Mo Shan
51Y.bmp

[addterminus]
1002
51Z Tsuen Wan
51Z.bmp

[addterminus]
81226371
VERS Date 31 JAN 2026
VERS.bmp
"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "all_routes.hof"
            path.write_text(contents, encoding="utf-8")
            entries = read_hof(path)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["destination"], "51Y Tai Mo Shan")
        self.assertEqual(entries[1]["destination"], "51Z Tsuen Wan")
        self.assertTrue(all(entry["bitmaps"] for entry in entries))

    def test_route_label_removes_direction_markers_but_keeps_real_suffixes(self):
        self.assertEqual(route_label("51Y Tai Mo Shan", "fallback"),
                         ("51", "Tai Mo Shan"))
        self.assertEqual(route_label("X42CY Yau Tong", "fallback"),
                         ("X42C", "Yau Tong"))
        self.assertEqual(route_label("A12A Foo Estate", "fallback"),
                         ("A12A", "Foo Estate"))


if __name__ == "__main__":
    unittest.main()
