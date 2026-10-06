"""Build a complete bus/fleet catalog from the public ACROSS list.

The generated files are deliberately kept out of source control by default.
Run from the repository root:

    python .\tools\across_catalog.py --output .\build\across

Use --refresh to re-fetch detail pages. The scraper is intentionally rate
limited because ACROSS is a community-maintained website.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE_URL = "https://1005.idv.hk/"
LIST_URL = urljoin(BASE_URL, "index.php?page=10")
DETAIL_URL = urljoin(BASE_URL, "index.php?page=11&p={record_id}")
LINK_RE = re.compile(r"href=\?page=11&p=(\d+)>(.*?)</a>", re.S)
FLEET_RE = re.compile(
    r"href=\?page=11&p=(?P<id>\d+)>(?P<fleet>[A-Za-z0-9][A-Za-z0-9 ./-]*)</a>"
)


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Hong-Kong-Assetto-Corsa catalog generator"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def operator_from_name(name: str) -> str:
    return name.split(" ", 1)[0]


def fleet_prefix(detail_html: str, record_id: str) -> str:
    values = []
    for match in FLEET_RE.finditer(detail_html):
        if match.group("id") != record_id:
            continue
        value = match.group("fleet").strip()
        if value not in values:
            values.append(value)
    if not values:
        return ""

    # ACROSS fleet numbers are generally a prefix followed by a sequence
    # number, e.g. E6X1 -> E6X or V6B230 -> V6B.
    prefixes = []
    for value in values:
        prefix = re.sub(r"\d+$", "", value)
        if prefix and prefix not in prefixes:
            prefixes.append(prefix)
    return "|".join(prefixes)


def fleet_count(detail_html: str, record_id: str) -> int:
    """Count ACROSS fleet entries shown on a model page."""
    return len(
        re.findall(
            rf"href=\?page=11&p={re.escape(record_id)}>([^<]+)</a>",
            detail_html,
        )
    )


def load_records(cache_dir: Path, refresh: bool, delay: float) -> list[dict[str, str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    list_cache = cache_dir / "index-page-10.html"
    if list_cache.exists() and not refresh:
        listing = list_cache.read_text(encoding="utf-8")
    else:
        listing = fetch(LIST_URL)
        list_cache.write_text(listing, encoding="utf-8")

    links = []
    seen = set()
    for match in LINK_RE.finditer(listing):
        record_id = match.group(1)
        if record_id in seen:
            continue
        seen.add(record_id)
        raw_name = re.sub(r"<[^>]+>", " ", match.group(2))
        links.append((record_id, " ".join(raw_name.split())))

    records = []
    for index, (record_id, model_name) in enumerate(links, start=1):
        detail_cache = cache_dir / f"detail-{record_id}.html"
        if detail_cache.exists() and not refresh:
            detail = detail_cache.read_text(encoding="utf-8")
        else:
            detail = fetch(DETAIL_URL.format(record_id=record_id))
            detail_cache.write_text(detail, encoding="utf-8")
            if index != len(links):
                time.sleep(delay)

        records.append(
            {
                "operator_code": operator_from_name(model_name),
                "across_record_id": record_id,
                "model_name": model_name,
                "fleet_prefix": fleet_prefix(detail, record_id),
                "fleet_count": fleet_count(detail, record_id),
                "source_url": DETAIL_URL.format(record_id=record_id),
            }
        )
        print(f"[{index}/{len(links)}] {model_name}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("build") / "across")
    parser.add_argument("--cache", type=Path, default=Path("build") / "across-cache")
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    records = load_records(args.cache, args.refresh, max(0.0, args.delay))
    args.output.mkdir(parents=True, exist_ok=True)

    fields = [
        "operator_code",
        "across_record_id",
        "model_name",
        "fleet_prefix",
        "fleet_count",
        "source_url",
    ]
    with (args.output / "across_bus_catalog.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

    (args.output / "across_bus_catalog.json").write_text(
        json.dumps(
            {
                "source": "https://1005.idv.hk/",
                "database": "ACROSS 7.4 (2024)",
                "record_count": len(records),
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = []
    for record in records:
        prefixes = record["fleet_prefix"].split("|") if record["fleet_prefix"] else [""]
        for prefix in prefixes:
            summary.append(
                {
                    "operator_code": record["operator_code"],
                    "fleet_prefix": prefix,
                    "model_name": record["model_name"],
                    "across_record_id": record["across_record_id"],
                    "listed_bus_count": record["fleet_count"],
                    "source_url": record["source_url"],
                }
            )
    summary.sort(
        key=lambda row: (
            row["operator_code"],
            row["fleet_prefix"],
            row["model_name"],
        )
    )
    summary_fields = [
        "operator_code",
        "fleet_prefix",
        "model_name",
        "across_record_id",
        "listed_bus_count",
        "source_url",
    ]
    with (args.output / "across_fleet_summary.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary)

    aggregate_map: dict[tuple[str, str], dict] = {}
    for row in summary:
        key = (row["operator_code"], row["fleet_prefix"])
        aggregate = aggregate_map.setdefault(
            key,
            {
                "operator_code": row["operator_code"],
                "fleet_prefix": row["fleet_prefix"],
                "listed_bus_count": 0,
                "model_names": [],
                "across_record_ids": [],
            },
        )
        aggregate["listed_bus_count"] += int(row["listed_bus_count"])
        if row["model_name"] not in aggregate["model_names"]:
            aggregate["model_names"].append(row["model_name"])
        if row["across_record_id"] not in aggregate["across_record_ids"]:
            aggregate["across_record_ids"].append(row["across_record_id"])
    aggregate_rows = list(aggregate_map.values())
    for row in aggregate_rows:
        row["model_names"] = " | ".join(row["model_names"])
        row["across_record_ids"] = "|".join(row["across_record_ids"])
    aggregate_rows.sort(
        key=lambda row: (
            row["operator_code"],
            -row["listed_bus_count"],
            row["fleet_prefix"],
        )
    )
    aggregate_fields = [
        "operator_code",
        "fleet_prefix",
        "listed_bus_count",
        "model_names",
        "across_record_ids",
    ]
    with (args.output / "across_code_counts.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=aggregate_fields)
        writer.writeheader()
        writer.writerows(aggregate_rows)

    (args.output / "across_fleet_summary.json").write_text(
        json.dumps(
            {
                "source": "https://1005.idv.hk/",
                "database": "ACROSS 7.4 (2024)",
                "note": "listed_bus_count counts fleet entries displayed on each ACROSS model page; it may include historical, spare, training, or retired entries depending on the record.",
                "rows": summary,
                "code_counts": aggregate_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} model records and {len(summary)} code rows to {args.output}")


if __name__ == "__main__":
    main()
