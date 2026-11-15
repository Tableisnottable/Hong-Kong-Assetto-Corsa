"""Collect the README's bounded Kam Tin pilot sources without touching the game.

Original downloads, provider URLs and machine-local paths stay in ignored source/.
Only a sanitised acquisition summary is suitable for Git. Existing files are
verified and retained; --refresh-index explicitly refreshes the source indexes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import threading
import urllib.parse
import urllib.request
import zipfile

from fetch_sources import FOUNDATION
from research_quality_sources import DATASETS, inspect_dataset, public, save

ROOT = Path(__file__).resolve().parents[1]
BOUNDS = [825184, 832215, 825535, 832871]
HOSTS = {
    "bulkdata.csdi.gov.hk", "open.hkmapservice.gov.hk", "download.map.gov.hk",
    "static.data.gov.hk", "data.gov.hk", "www.landsd.gov.hk",
    "download.geofabrik.de", "api.openstreetmap.org", "www.openstreetmap.org",
}
EXTRAS = {
    "ib1000_GML_resources.zip": "https://open.hkmapservice.gov.hk/OpenData/opendata_static/resources/resources_iB1000_GML.zip",
    "td_road_network_v2.gdb.zip": "https://static.data.gov.hk/td/road-network-v2/RdNet_IRNP.gdb.zip",
    "td_road_network_spec.zip": "https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip",
    "td_road_network_files.csv": "https://static.data.gov.hk/td/road-network-v2/dataspec/file_list.csv",
    "data_gov_hk_terms.html": "https://data.gov.hk/en/terms-and-conditions",
    "osm_copyright.html": "https://www.openstreetmap.org/copyright",
}
TILE_FIELDS = {
    "ib1000": ("SHEETNO", "GML"),
    "lidar_dtm_2020": ("TILE_NAME", "URL"),
    "nontextured_models": ("SHEETNO", "Format_glTF"),
    "bit00": ("SHEETNO", "Format_FBX"),
    "tdop": ("SHEETNO", "DOWNLOAD_LINK"),
    "individualised_models": ("SHEETNO", "Format_glTF"),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in HOSTS:
        raise ValueError("Source or redirect is outside the approved public hosts")
    return url


def inspect_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        unpacked = sum(item.file_size for item in entries)
        if unpacked > 8 * 1024**3 or len(entries) > 30000:
            raise ValueError("Archive exceeds the local inspection budget")
        for item in entries:
            normal = item.filename.replace("\\", "/")
            if normal.startswith("/") or ":" in normal or ".." in Path(normal).parts:
                raise ValueError("Unsafe archive entry")
        bad = archive.testzip()
        if bad:
            raise ValueError("Archive CRC failed")
        return {"crc": "PASS", "entries": len(entries), "uncompressed_bytes": unpacked,
                "extensions": sorted({Path(i.filename).suffix.lower() for i in entries if not i.is_dir()})}


class Collector:
    def __init__(self, raw, total_mib, file_mib):
        self.raw = raw
        self.limit = total_mib * 1024**2
        self.file_limit = file_mib * 1024**2
        self.network_bytes = 0
        self.lock = threading.Lock()

    def fetch(self, task):
        name, kind, url, destination, candidates = task
        record = {"name": name, "role": kind, "source_url": public(url)}
        try:
            checked_url(url)
            candidate = next((p for p in candidates if p and p.is_file()), None)
            if destination.is_file():
                path, action = destination, "retained"
                first_action = ("reused_in_place" if kind == "individualised_models" and candidate
                                else "copied_existing_source" if candidate else "downloaded")
            elif candidate and kind == "individualised_models":
                # Multi-gigabyte scenery is already available locally. Reference
                # its verified archive, rather than making another large copy.
                path, action, first_action = candidate, "reused_in_place", "reused_in_place"
            elif candidate:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, destination)
                path, action, first_action = destination, "copied_existing_source", "copied_existing_source"
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_suffix(destination.suffix + ".partial")
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "HK1to1-MapData/1.0"})
                    with urllib.request.urlopen(req, timeout=240) as response:
                        checked_url(response.url)
                        expected = int(response.headers.get("Content-Length", "0"))
                        if expected > self.file_limit:
                            raise ValueError("Download exceeds per-file budget")
                        received = 0
                        with temporary.open("wb") as out:
                            while chunk := response.read(1024**2):
                                received += len(chunk)
                                with self.lock:
                                    self.network_bytes += len(chunk)
                                    if self.network_bytes > self.limit:
                                        raise ValueError("Download exceeds total run budget")
                                if received > self.file_limit:
                                    raise ValueError("Download exceeds per-file budget")
                                out.write(chunk)
                        if expected and received != expected:
                            raise ValueError("Download length differs from HTTP Content-Length")
                    if destination.suffix.lower() in {".zip", ".kmz"}:
                        inspect_archive(temporary)
                    temporary.replace(destination)
                finally:
                    temporary.unlink(missing_ok=True)
                path, action, first_action = destination, "downloaded", "downloaded"
            record.update(status="PASS", action=action, first_action=first_action,
                          bytes=path.stat().st_size, sha256=digest(path))
            if path.suffix.lower() in {".zip", ".kmz"}:
                record["archive"] = inspect_archive(path)
            try:
                record["file"] = path.relative_to(ROOT).as_posix()
            except ValueError:
                record["file"] = "external_source/" + path.name
            record["local_path"] = str(path.resolve())
        except Exception as error:
            # Never publish exception URLs: a provider can embed a download key.
            record.update(status="FAILED", error_type=type(error).__name__)
        print(f"{record['status']}: {kind} / {name}", flush=True)
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse-project", type=Path, help="Existing HK_1to1_Project folder, read-only")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "source/map_build_20261115")
    parser.add_argument("--refresh-index", action="store_true")
    parser.add_argument("--total-mib", type=int, default=3072)
    parser.add_argument("--file-mib", type=int, default=1536)
    args = parser.parse_args()
    if args.total_mib <= 0 or args.file_mib <= 0:
        parser.error("Download budgets must be positive")
    raw = args.source_dir.resolve()
    if not raw.is_relative_to((ROOT / "source").resolve()):
        parser.error("Keep acquired data inside this project's ignored source directory")
    raw.mkdir(parents=True, exist_ok=True)
    index = raw / "index"
    datasets = dict(DATASETS, individualised_models="landsd_rcd_1671676915450_88604")
    summaries, features = {}, {}
    for name, dataset_id in datasets.items():
        cache = index / f"{name}_features.json"
        if args.refresh_index or not cache.is_file():
            _, _, rows = inspect_dataset((name, dataset_id), BOUNDS, index)
        else:
            rows = json.loads(cache.read_text(encoding="utf-8"))["features"]
        features[name] = rows
        summaries[name] = {"dataset_id": dataset_id, "records_intersecting_pilot": len(rows),
                           "metadata_url": f"https://portal.csdi.gov.hk/geoportal/rest/metadata/item/{dataset_id}"}
    tasks = []
    legacy = args.reuse_project.resolve() / "source" if args.reuse_project else None
    for filename, url in FOUNDATION.items():
        tasks.append((filename, "hk_foundation", url, ROOT / "source" / filename,
                      [legacy / filename] if legacy else []))
    for name, (sheet_field, url_field) in TILE_FIELDS.items():
        for row in features[name]:
            attrs = row["attributes"]
            sheet = str(attrs[sheet_field])
            filename = f"{name}_{sheet}.zip"
            candidates = [ROOT / "source/quality_research" / filename]
            candidates.extend(p for p in (ROOT / "source/quality_research").glob(name + "_*.zip")
                              if p.name.replace("-", "") == filename.replace("-", ""))
            if name == "individualised_models" and legacy:
                candidates.append(legacy / "csdi_individualised" / f"{sheet}_GLTF.zip")
            tasks.append((filename, name, attrs[url_field], raw / "archives" / filename, candidates))
    for filename, url in EXTRAS.items():
        tasks.append((filename, "dictionary_terms_or_network", url, raw / "references" / filename, []))
    collector = Collector(raw, args.total_mib, args.file_mib)
    # Submit the orthophoto first: its server can take longer to prepare a tile.
    tasks.sort(key=lambda item: item[1] != "tdop")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(collector.fetch, task) for task in tasks]
        from concurrent.futures import as_completed
        records = [future.result() for future in as_completed(futures)]
    records.sort(key=lambda r: (r["role"], r["name"]))
    origin_actions = {name: sum(r["first_action"] == name for r in records)
                      for name in ("downloaded", "copied_existing_source", "reused_in_place")}
    origin_bytes = sum(r["bytes"] for r in records if r["first_action"] == "downloaded")
    report = {
        "collected_hong_kong_date": str(datetime.now(timezone(timedelta(hours=8))).date()),
        "scope": "README checkpoint 1-2 pilot data, plus retained Hong Kong-wide foundation and road network",
        "bounds_epsg2326": BOUNDS, "origin_epsg2326": [826000, 833000],
        "download_budget_mib": args.total_mib, "network_bytes_this_run": collector.network_bytes,
        "original_acquisition": {"file_actions": origin_actions,
                                  "downloaded_source_bytes": origin_bytes,
                                  "downloaded_source_mib": round(origin_bytes / 1024**2, 2)},
        "datasets": summaries, "files": records,
        "status": "PASS" if all(r["status"] == "PASS" for r in records) else "INCOMPLETE",
        "limits": [
            "Acquisition and archive integrity only; no map build or game installation.",
            "Tile outlines intersect the pilot envelope, not all of the 6x6 km region or Hong Kong.",
            "Capture dates, coordinate datums and attribute code meanings require source-specific review.",
            "Road edges, deck levels, facades, collision and car-height review still need authoring.",
            "Retained foundation snapshots are reused unchanged, not presented as newly surveyed data.",
        ],
    }
    save(raw / "local_manifest.json", report)
    for record in records:
        record.pop("local_path", None)
    save(ROOT / "reports/map_data_acquisition.json", public(report))
    print(json.dumps({"status": report["status"], "files": len(records),
                      "failed": [r["name"] for r in records if r["status"] != "PASS"],
                      "network_mib": round(collector.network_bytes / 1024**2, 2)}, indent=2))
    raise SystemExit(report["status"] != "PASS")


if __name__ == "__main__":
    main()
