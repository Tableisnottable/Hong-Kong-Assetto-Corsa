"""Generate missing Content Manager preview.jpg and livery.png files locally.

Requires Blender 5.x, numpy and Pillow. Does not start AC or change bus models.
Rendered pictures remain local; only this generator is intended for GitHub.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageStat
from prepare_kmb_ai_grid import ROOT, buses, write_backed_up
from repair_omsi_bus_physics import AC


def valid_picture(path):
    if not path.is_file():
        return False
    try:
        with Image.open(path) as picture:
            picture.verify()
        return True
    except (OSError, ValueError):
        return False


def render_one(blender, car, skins, out, reuse=False):
    out.mkdir(parents=True, exist_ok=True)
    log = out / "blender.log"
    if not (reuse and all(valid_picture(out / skin / "preview.png") for skin in skins)):
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run([str(blender), "--background", "--factory-startup", "--python-exit-code", "1",
                "--python", str(ROOT / "tools/blender/render_bus_preview.py"), "--", str(car), str(out), *skins],
                stdout=stream, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            raise RuntimeError("Blender preview failed; see " + str(log))
    for skin in skins:
        path = out / skin / "preview.png"
        if not valid_picture(path):
            raise ValueError("Missing or unreadable render: " + str(path))
        with Image.open(path) as picture:
            if min(picture.size) < 500 or max(ImageStat.Stat(picture.convert("RGB")).stddev) < 5:
                raise ValueError("Render is unexpectedly small/blank: " + str(path))
            picture.convert("RGB").save(path.with_suffix(".jpg"), "JPEG", quality=95)
    print(f"Rendered {car.name}: {len(skins)} skin(s)", flush=True)
    return car, skins, out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--blender", type=Path, default=Path(r"C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"))
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/bus_previews")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--reuse-renders", action="store_true", help="Resume installation from existing PNG renders in --output; use only if models/skins are unchanged")
    args = parser.parse_args()
    jobs, icons = [], []
    for bus in buses():
        car = args.ac / "content/cars" / bus["id"]
        skins = []
        for skin in sorted((car / "skins").iterdir()):
            if not skin.is_dir():
                continue
            if not any(valid_picture(skin / ("preview" + ext)) for ext in (".jpg", ".png")):
                skins.append(skin.name)
            if not valid_picture(skin / "livery.png"):
                icons.append(skin)
        if skins:
            jobs.append((args.blender, car, skins, args.output / car.name, args.reuse_renders))
    backup = args.output / "backups" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    records = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda task: render_one(*task), jobs))
    for car, skins, out in results:
        for skin in skins:
            src = out / skin / "preview.jpg"
            dest = car / "skins" / skin / "preview.jpg"
            if args.install:
                write_backed_up(dest, src.read_bytes(), backup / car.name / skin)
            records.append({"car": car.name, "skin": skin, "preview": str(dest if args.install else src),
                            "sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
    for skin in icons:
        picture = Image.new("RGB", (64, 64), (194, 18, 27))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(picture)
        draw.rectangle((0, 42, 63, 63), fill=(228, 213, 179))
        draw.text((12, 13), "KMB", fill="white")
        icon = args.output / skin.parent.parent.name / skin.name / "livery.png"
        icon.parent.mkdir(parents=True, exist_ok=True)
        picture.save(icon)
        if args.install:
            write_backed_up(skin / "livery.png", icon.read_bytes(), backup / skin.parent.parent.name / skin.name)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"status": "PASS", "rendered": records, "livery_icons": len(icons), "installed": args.install,
              "note": "Images only; Content Manager may need a list refresh or restart"}
    (args.output / "preview_installation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
