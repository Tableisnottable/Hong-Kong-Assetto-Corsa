"""Catalogue existing local scenery downloads, refusing error responses posing as ZIPs.

No file is deleted, extracted or trusted for production. Full CRC verification
is limited by an explicit compressed-byte budget; other ZIPs remain unverified.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import zipfile

from collect_build_data import ROOT, digest
from research_quality_sources import save


def inspect_header(path):
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            for member in members:
                name = member.filename.replace("\\", "/")
                if name.startswith("/") or ":" in name or ".." in Path(name).parts:
                    return {"status": "UNSAFE_MEMBERS"}
            return {"status": "ZIP_DIRECTORY_ONLY", "members": len(members),
                    "uncompressed_bytes": sum(m.file_size for m in members),
                    "extensions": dict(Counter(Path(m.filename).suffix.lower() for m in members if not m.is_dir()))}
    except (zipfile.BadZipFile, OSError):
        with path.open("rb") as stream:
            header = stream.read(256).lstrip().lower()
        kind = ("html_response" if header.startswith((b"<!doctype html", b"<html")) else
                "json_response" if header.startswith((b"{", b"[")) else "other_or_truncated")
        return {"status": "INVALID_ZIP", "payload_kind": kind}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crc-budget-mib", type=int, default=3072)
    args = parser.parse_args()
    if args.crc_budget_mib < 0:
        parser.error("CRC budget cannot be negative")
    repository = ROOT.parents[1]
    files = sorted(p for name in ("all_3324_zips", "raw_zips") for p in (repository / name).glob("*.zip"))
    records = []
    for path in files:
        record = {"file": path.relative_to(repository).as_posix(), "sheet_name_candidate": path.stem,
                  "bytes": path.stat().st_size, **inspect_header(path)}
        records.append(record)
    # Prioritize the explicitly retained Tin Kwong sheet, then valid small archives.
    candidates = sorted((r for r in records if r["status"] == "ZIP_DIRECTORY_ONLY"),
                        key=lambda r: (r["sheet_name_candidate"] != "11-SW-9D", r["bytes"]))
    used = 0
    for record in candidates:
        if used + record["bytes"] > args.crc_budget_mib * 1024**2:
            continue
        if record["uncompressed_bytes"] > 8 * 1024**3 or record["members"] > 30000:
            record["status"] = "REQUIRES_LARGER_INSPECTION_BUDGET"
            continue
        path = repository / record["file"]
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
            record["status"] = "CRC_FAILED" if bad else "CRC_PASS"
            if not bad:
                record["sha256"] = digest(path)
        except (zipfile.BadZipFile, RuntimeError, OSError, EOFError):
            record["status"] = "CRC_FAILED"
        used += record["bytes"]
        print(f"Legacy archive: {record['sheet_name_candidate']} / {record['status']}", flush=True)
    local = ROOT / "source/hong_kong_master/legacy_archive_inventory.json"
    save(local, {"scope": "Legacy download integrity only; provenance and geometry unreviewed", "files": records})
    statuses = Counter(r["status"] for r in records)
    summary = {"scope": "Existing local map download integrity audit", "archive_files": len(records),
               "total_bytes": sum(r["bytes"] for r in records), "counts_by_status": dict(statuses),
               "crc_budget_mib": args.crc_budget_mib, "crc_checked_compressed_bytes": used,
               "invalid_payload_types": dict(Counter(r["payload_kind"] for r in records if r["status"] == "INVALID_ZIP")),
               "inventory": local.relative_to(ROOT).as_posix(),
               "limits": ["No file deleted, extracted, installed or copied into a build.",
                          "ZIP_DIRECTORY_ONLY is not integrity approval. CRC_PASS does not establish source provenance, geometric accuracy or licence.",
                          "Legacy filenames are sheet candidates; format and official dataset identity need independent matching."]}
    save(ROOT / "reports/legacy_archive_audit.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
