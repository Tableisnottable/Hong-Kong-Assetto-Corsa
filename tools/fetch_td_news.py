# -*- coding: utf-8 -*-
"""Fetch Hong Kong Transport Department special traffic news.

Source: https://resource.data.one.gov.hk/td/sc/specialtrafficnews.xml
(Open Data provided by Transport Department, HK SAR Government)

Output:
    config/td_traffic_news.json       parsed, deduplicated news items
    apps/lua/hk_exam/td_news.lua      Lua table for the in-game exam app

Usage:
    python tools/fetch_td_news.py
    python tools/fetch_td_news.py --lang en
"""

import argparse
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "config" / "td_traffic_news.json"
OUT_LUA = ROOT / "apps" / "lua" / "hk_exam" / "td_news.lua"

SOURCES = {
    "sc": "https://resource.data.one.gov.hk/td/sc/specialtrafficnews.xml",
    "tc": "https://resource.data.one.gov.hk/td/tc/specialtrafficnews.xml",
    "en": "https://resource.data.one.gov.hk/td/en/specialtrafficnews.xml",
}

NS = "{http://data.one.gov.hk/td}"

# Incident type inference from text (Traditional Chinese + English keywords)
CATEGORIES = [
    ("accident", ("交通意外", "意外", "碰撞", "accident", "collision")),
    ("roadworks", ("道路工程", "維修", "施工", "roadworks", "maintenance", "works")),
    ("congestion", ("擠塞", "車龍", "交通繁忙", "congestion", "traffic queue", "heavy traffic")),
    ("closure", ("封閉", "封路", "全線", "closed", "closure")),
    ("reopened", ("解封", "重開", "恢復", "re-opened", "reopened", "resumed")),
    ("weather", ("天氣", "暴雨", "颱風", "水浸", "weather", "rainstorm", "typhoon", "flood")),
    ("event", ("活動", "賽事", "遊行", "event", "race", "procession")),
]


def classify(text: str) -> str:
    low = text.lower()
    for name, keys in CATEGORIES:
        if any(k.lower() in low for k in keys):
            return name
    return "other"


def lua_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")


def fetch(lang: str) -> list[dict]:
    url = SOURCES[lang]
    req = urllib.request.Request(url, headers={"User-Agent": "HK-AC-Project/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()

    root = ET.fromstring(raw)
    items = []
    for msg in root.findall(f"{NS}message"):
        def text(tag):
            node = msg.find(f"{NS}{tag}")
            return (node.text or "").strip() if node is not None else ""

        chin = text("ChinText")
        eng = text("EngText")
        primary = chin or eng
        items.append({
            "id": text("msgID"),
            "status": text("CurrentStatus"),
            "title_zh": text("ChinShort") or chin,
            "title_en": text("EngShort") or eng,
            "text_zh": chin,
            "text_en": eng,
            "category": classify(primary + " " + eng),
            "reopened": "解封" in primary or "re-open" in eng.lower(),
            "announced": text("AnnounceDate"),
        })
    return items


def write_lua(items: list[dict]) -> None:
    lines = [
        "-- HK TD special traffic news (auto-generated)",
        f"-- Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "-- Source: https://resource.data.one.gov.hk/td/sc/specialtrafficnews.xml",
        "",
        "return {",
    ]
    for it in items:
        lines.append("  {")
        lines.append(f'    id = "{lua_escape(it["id"])}",')
        lines.append(f'    category = "{lua_escape(it["category"])}",')
        lines.append(f'    reopened = {"true" if it["reopened"] else "false"},')
        lines.append(f'    title_zh = "{lua_escape(it["title_zh"])}",')
        lines.append(f'    title_en = "{lua_escape(it["title_en"])}",')
        lines.append("  },")
    lines.append("}")
    OUT_LUA.parent.mkdir(parents=True, exist_ok=True)
    OUT_LUA.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="sc", choices=sorted(SOURCES))
    args = ap.parse_args()

    items = fetch(args.lang)
    # Active incidents first, reopened ones last.
    items.sort(key=lambda i: (i["reopened"], i["category"]))

    payload = {
        "source": SOURCES[args.lang],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_lua(items)

    active = sum(1 for i in items if not i["reopened"])
    by_cat = {}
    for i in items:
        by_cat[i["category"]] = by_cat.get(i["category"], 0) + 1
    print(f"[OK] {len(items)} messages ({active} active) -> {OUT_JSON.name}, {OUT_LUA.name}")
    print(f"     categories: {by_cat}")


if __name__ == "__main__":
    main()
