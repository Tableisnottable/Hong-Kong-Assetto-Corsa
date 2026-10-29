# -*- coding: utf-8 -*-
"""Regenerate docs/traffic_vehicle_list.md from config/vehicles.json with proper UTF-8."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
with open(ROOT / "config" / "vehicles.json", encoding="utf-8") as f:
    data = json.load(f)

vehicles = data["vehicles"]
private = [v for v in vehicles if v.get("category") == "private"]
commercial = [v for v in vehicles if v.get("category") == "commercial"]
public_special = [v for v in vehicles if v.get("category") == "public_special"]
other = [v for v in vehicles if v.get("category") not in ("private", "commercial", "public_special")]


def row(v):
    dims = v.get("dimensions_m", {})
    dim = f"{dims.get('length','?')}×{dims.get('width','?')}×{dims.get('height','?')}" if dims else "?"
    return (
        f"| {v.get('display_name', v['id'])} | {v.get('year','?')} | "
        f"{v.get('body_type','?')} | {dim} | {v.get('engine','?')} | "
        f"{v.get('power_hp','?')} | {v.get('transmission','?')} | {v.get('notes','')} |"
    )


lines = []
lines.append("# 香港交通車輛清單 / Hong Kong Traffic Vehicle List\n")
lines.append("本清單由 `config/vehicles.json` 自動生成，涵蓋 **%d** 台車輛。\n" % len(vehicles))
lines.append("> 注意：所有車輛均屬 `original_model_required`，即需要自行取得/製作 3D 模型後才能用於遊戲。\n")

lines.append("## 目標車流比例 / Target Traffic Mix\n")
lines.append("| 類別 | 數量 | 比例 |")
lines.append("|---|---:|---:|")
lines.append("| 私家車 Private | %d | %d%% |" % (len(private), round(100 * len(private) / len(vehicles))))
lines.append("| 商用車 Commercial | %d | %d%% |" % (len(commercial), round(100 * len(commercial) / len(vehicles))))
lines.append("| 公共/特殊 Public & Special | %d | %d%% |" % (len(public_special), round(100 * len(public_special) / len(vehicles))))

lines.append("\n---\n")
lines.append("### 私家車 / Private Cars (%d)\n" % len(private))
lines.append("| 車款 Vehicle | 年份 | 車身 Body | 尺寸 L×W×H (m) | 引擎 Engine | 馬力 hp | 波箱 Gearbox | 備註 |")
lines.append("|---|---|---|---|---|---|---|---|")
for v in private:
    lines.append(row(v))

lines.append("\n### 商用車 / Commercial (%d)\n" % len(commercial))
lines.append("| 車款 Vehicle | 年份 | 車身 Body | 尺寸 L×W×H (m) | 引擎 Engine | 馬力 hp | 波箱 Gearbox | 備註 |")
lines.append("|---|---|---|---|---|---|---|---|")
for v in commercial:
    lines.append(row(v))

lines.append("\n### 公共/特殊車輛 / Public & Special (%d)\n" % len(public_special))
lines.append("| 車款 Vehicle | 年份 | 車身 Body | 尺寸 L×W×H (m) | 引擎 Engine | 馬力 hp | 波箱 Gearbox | 備註 |")
lines.append("|---|---|---|---|---|---|---|---|")
for v in public_special:
    lines.append(row(v))

if other:
    lines.append("\n### 其他 / Other (%d)\n" % len(other))
    lines.append("| 車款 Vehicle | 年份 | 車身 Body | 尺寸 L×W×H (m) | 引擎 Engine | 馬力 hp | 波箱 Gearbox | 備註 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for v in other:
        lines.append(row(v))

out = ROOT / "docs" / "traffic_vehicle_list.md"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"[OK] Regenerated {out} ({len(lines)} lines, {len(vehicles)} vehicles)")
