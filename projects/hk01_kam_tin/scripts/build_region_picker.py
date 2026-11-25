"""Build a standalone browser map for selecting Hong Kong authoring regions."""
from __future__ import annotations

from base64 import b64encode
from io import BytesIO
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/python_deps"))

from PIL import Image, ImageDraw


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    master = ROOT / "gis/hong_kong_master"
    regions = read_json(master / "regions.json")["regions"]
    centres = read_json(master / "exam_route_name_candidates.json")["centres"]
    roads = read_json(master / "hk_roads_grid.json")["roads"]
    loop = read_json(ROOT / "driving_test/source/test_loop_source.json")["xy"]
    centre_by_id = {centre["id"]: centre for centre in centres}

    west = min(region["bounds_epsg2326"][0] for region in regions)
    south = min(region["bounds_epsg2326"][1] for region in regions)
    east = max(region["bounds_epsg2326"][2] for region in regions)
    north = max(region["bounds_epsg2326"][3] for region in regions)
    padding, scale = 24, 0.024
    size = (round((east - west) * scale) + padding * 2,
            round((north - south) * scale) + padding * 2)

    def pixel(easting, northing):
        return padding + (easting - west) * scale, padding + (north - northing) * scale

    map_image = Image.new("RGB", size, "#12252d")
    draw = ImageDraw.Draw(map_image)
    for is_public, color in ((False, "#926b54"), (True, "#80b2a5")):
        for road in roads:
            if (road["access_state"] == "public_candidate") == is_public:
                draw.line([pixel(*point) for point in road["xy"]], fill=color, width=1)

    draw.line([pixel(*point) for point in loop], fill="#d4f880", width=4)
    for centre in centres:
        x, y = pixel(*centre["approximate_location_epsg2326"])
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#ffc477", outline="#12252d")

    pilot_region = next(region["id"] for region in regions
                        if region["bounds_epsg2326"][0] <= loop[0][0] < region["bounds_epsg2326"][2]
                        and region["bounds_epsg2326"][1] <= loop[0][1] < region["bounds_epsg2326"][3])
    for region in regions:
        e0, n0, e1, n1 = region["bounds_epsg2326"]
        x0, y0 = pixel(e0, n1)
        x1, y1 = pixel(e1, n0)
        region["map_percent"] = [100 * x0 / size[0], 100 * y0 / size[1],
                                 100 * (x1 - x0) / size[0], 100 * (y1 - y0) / size[1]]
        region["exam_centres"] = [centre_by_id[key] for key in region["exam_centres"]]

    png = BytesIO()
    map_image.save(png, format="PNG")
    data = json.dumps({"regions": regions, "pilotRegion": pilot_region}).replace("<", "\\u003c")
    template = Path(__file__).with_name("region_picker.html").read_text(encoding="utf-8")
    page = template.replace("MAP_PNG_BASE64", b64encode(png.getvalue()).decode("ascii"))
    destination = master / "region_picker.html"
    destination.write_text(page.replace("REGION_DATA_JSON", data), encoding="utf-8")
    print(f"Open {destination} ({len(regions)} regions)")


if __name__ == "__main__":
    main()
