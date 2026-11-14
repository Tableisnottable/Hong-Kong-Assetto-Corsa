"""Inspect official data for a bounded quality pilot; never alter game content.

Raw government responses and optional small sample ZIPs stay in ignored source/.
The published report contains metadata/counts, not downloaded geographic data.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
import struct
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "buildings": "landsd_rcd_1637211194312_35158",
    "lidar_dtm_2020": "cedd_rcd_1629267205233_87895",
    "ib1000": "landsd_rcd_1637223748322_25497",
    "nontextured_models": "landsd_rcd_1742809441342_98380",
    "tdop": "landsd_rcd_1701762716904_4826",
    "bit00": "landsd_rcd_1637306559892_42396",
}
NS = {"gmd": "http://www.isotc211.org/2005/gmd", "gco": "http://www.isotc211.org/2005/gco"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "HK1to1-QualityResearch/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        payload = response.read(20 * 1024**2 + 1)
    if len(payload) > 20 * 1024**2:
        raise RuntimeError("Metadata response exceeds size limit")
    result = json.loads(payload)
    if result.get("error"):
        raise RuntimeError(str(result["error"]))
    return result


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public(value):
    """Download index URLs can contain provider keys; omit them from publication."""
    if isinstance(value, dict):
        return {k: public(v) for k, v in value.items()}
    if isinstance(value, list):
        return [public(v) for v in value]
    if isinstance(value, str) and value.startswith("https://"):
        parts = urllib.parse.urlsplit(value)
        query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query)
                 if k.lower() not in {"key", "token", "access_token", "signature"}]
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
    return value


def xml_metadata(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from xml_metadata(item)
    elif isinstance(value, list):
        for item in value:
            yield from xml_metadata(item)
    elif isinstance(value, str) and "<gmd:MD_Metadata" in value:
        yield ET.fromstring(value)


def inspect_dataset(item, bounds, raw):
    name, dataset_id = item
    service = f"https://portal.csdi.gov.hk/server/rest/services/common/{dataset_id}/FeatureServer/0"
    metadata_url = f"https://portal.csdi.gov.hk/geoportal/rest/metadata/item/{dataset_id}"
    metadata = get(metadata_url)
    layer = get(service + "?f=json")
    params = {"f": "json", "where": "1=1", "geometry": ",".join(map(str, bounds)),
              "geometryType": "esriGeometryEnvelope", "inSR": 2326,
              "spatialRel": "esriSpatialRelIntersects", "returnIdsOnly": "true"}
    ids = get(service + "/query?" + urllib.parse.urlencode(params))
    object_ids = sorted(ids.get("objectIds") or [])
    if len(object_ids) > 5000:
        raise RuntimeError("Pilot exceeds 5000 records; reduce bounds")
    features = []
    for start in range(0, len(object_ids), 200):
        query = {"f": "json", "objectIds": ",".join(map(str, object_ids[start:start + 200])),
                 "outFields": "*", "returnGeometry": "true", "outSR": 2326}
        page = get(service + "/query?" + urllib.parse.urlencode(query))
        if page.get("exceededTransferLimit"):
            raise RuntimeError("Server truncated pilot query")
        features.extend(page.get("features", []))
    if len(features) != len(object_ids):
        raise RuntimeError("Source record count changed or query incomplete; retry")
    save(raw / f"{name}_metadata.json", metadata)
    save(raw / f"{name}_layer.json", layer)
    save(raw / f"{name}_features.json", {"spatialReference": {"wkid": 2326}, "features": features})
    report = {"dataset_id": dataset_id, "metadata_url": metadata_url,
              "portal_url": f"https://portal.csdi.gov.hk/geoportal/?datasetId={dataset_id}",
              "service": service, "layer_name": layer.get("name"), "count_in_pilot_envelope": len(features),
              "fields": [f["name"] for f in layer.get("fields", [])]}
    for xml in xml_metadata(metadata):
        for label, xpath in [("abstract", ".//gmd:abstract/gco:CharacterString"),
                             ("lineage", ".//gmd:statement/gco:CharacterString"),
                             ("use_limitations", ".//gmd:useLimitation/gco:CharacterString")]:
            report[label] = [e.text for e in xml.findall(xpath, NS) if e.text]
    if name == "buildings":
        heights = [f["attributes"] for f in features]
        valid = [a for a in heights if isinstance(a.get("BaseHeight"), (int, float))
                 and isinstance(a.get("TopHeight"), (int, float))
                 and a["TopHeight"] > a["BaseHeight"]]
        report["height_coverage"] = {"base_and_top_positive_difference": len(valid),
                                     "missing_or_invalid_base_top": len(heights) - len(valid),
                                     "note": "Top/Base are datum heights; use TopHeight-BaseHeight, not TopHeight as extrusion."}
    else:
        report["tiles"] = [public(f["attributes"]) for f in features]
    return name, report, features


def sample_archive(url, destination):
    allowed = {"bulkdata.csdi.gov.hk", "open.hkmapservice.gov.hk"}
    if urllib.parse.urlsplit(url).hostname not in allowed:
        raise RuntimeError("Unexpected sample archive host")
    limit = 32 * 1024**2
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "HK1to1-QualityResearch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        if urllib.parse.urlsplit(response.url).hostname not in allowed:
            raise RuntimeError("Unexpected sample redirect host")
        if int(response.headers.get("Content-Length", "0")) > limit:
            raise RuntimeError("Sample archive exceeds 32 MiB limit")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise RuntimeError("Sample archive exceeds 32 MiB limit")
    destination.write_bytes(data)
    with zipfile.ZipFile(destination) as archive:
        if any(e.file_size > 150 * 1024**2 for e in archive.infolist()):
            raise RuntimeError("Sample entry exceeds inspection limit")
        bad = archive.testzip()
        if bad:
            raise RuntimeError("Sample ZIP CRC failed")
        result = {"source_url": public(url), "local_file": destination.name,
                  "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                  "zip_crc_passed": True, "members": archive.namelist()}
        result["geotiff_grids"] = {}
        for name in archive.namelist():
            if name.lower().endswith((".tif", ".tiff")):
                with archive.open(name) as stream:
                    header = stream.read(8)
                    order = {b"II": "<", b"MM": ">"}.get(header[:2])
                    if not order or struct.unpack(order + "H", header[2:4])[0] != 42:
                        raise RuntimeError("Sample inspection requires classic TIFF")
                    stream.seek(struct.unpack(order + "I", header[4:8])[0])
                    count = struct.unpack(order + "H", stream.read(2))[0]
                    entries = [stream.read(12) for _ in range(count)]
                    grid = {}
                    labels = {256: "width_pixels", 257: "height_pixels", 33550: "model_pixel_scale",
                              33922: "model_tiepoints"}
                    for entry in entries:
                        tag, kind, count, offset = struct.unpack(order + "HHII", entry)
                        if tag not in labels:
                            continue
                        code, size = {3: ("H", 2), 4: ("I", 4), 12: ("d", 8)}[kind]
                        if count > 24:
                            raise RuntimeError("Unexpected TIFF georeference tag size")
                        if count * size > 4:
                            stream.seek(offset)
                            values = stream.read(count * size)
                        else:
                            values = entry[8:8 + count * size]
                        values = struct.unpack(order + code * count, values)
                        grid[labels[tag]] = values[0] if count == 1 else list(values)
                    grid["note"] = "Pixel spacing is not a vertical-accuracy claim; datum/CRS require source metadata."
                    result["geotiff_grids"][name] = grid
        result["ascii_headers"] = {}
        for name in archive.namelist():
            if name.lower().endswith(".asc"):
                with archive.open(name) as stream:
                    result["ascii_headers"][name] = [stream.readline().decode("ascii").strip() for _ in range(6)]
        result["gml_feature_types"] = {}
        for name in archive.namelist():
            if name.lower().endswith(".gml"):
                counts = {}
                with archive.open(name) as stream:
                    for _, element in ET.iterparse(stream, events=("end",)):
                        local = element.tag.split("}")[-1]
                        if local in {"featureMember", "member"} and len(element):
                            kind = element[0].tag.split("}")[-1]
                            counts[kind] = counts.get(kind, 0) + 1
                            element.clear()
                result["gml_feature_types"][name] = counts
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bounds", nargs=4, type=float, default=[825184, 832215, 825535, 832871],
                        metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--probe-sheet", help="Optionally fetch one matching LiDAR DTM and iB1000 GML ZIP (32 MiB maximum each)")
    args = parser.parse_args()
    west, south, east, north = args.bounds
    if not (west < east and south < north and (east - west) * (north - south) <= 4_000_000):
        parser.error("Require a positive envelope no larger than 4 square kilometres")
    raw = ROOT / "source/quality_research"
    report = {"checked_local_date": str(datetime.now(timezone(timedelta(hours=8))).date()),
              "scope": "Research only; no game installation or quality approval",
              "bounds_epsg2326": args.bounds, "selection": "Envelope around test checkpoints 1-2; final corridor selection pending",
              "datasets": {}, "sample_archives": []}
    features = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        for name, record, rows in executor.map(lambda item: inspect_dataset(item, args.bounds, raw), DATASETS.items()):
            report["datasets"][name] = record
            features[name] = rows
            print(f"{name}: {len(rows)} records", flush=True)
    if args.probe_sheet:
        for name, sheet_field, url_field in [("lidar_dtm_2020", "TILE_NAME", "URL"), ("ib1000", "SHEETNO", "GML")]:
            matches = [f["attributes"] for f in features[name]
                       if str(f["attributes"][sheet_field]).replace("-", "") == args.probe_sheet.replace("-", "")]
            if len(matches) != 1:
                raise RuntimeError("Probe sheet must match exactly one tile in the pilot envelope")
            result = sample_archive(matches[0][url_field], raw / f"{name}_{args.probe_sheet}.zip")
            report["sample_archives"].append(result)
            print(f"{name}: sample CRC passed, {result['bytes']} bytes", flush=True)
    output = ROOT / "reports/high_quality_source_research.json"
    save(output, report)
    print("Report:", output)


if __name__ == "__main__":
    main()
