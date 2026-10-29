# -*- coding: utf-8 -*-
"""Fix garbled README traffic section: replace by byte offset search."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

p = Path("README.md")
raw = p.read_bytes()

marker = b"## ???? / CSP Traffic Mode"
idx = raw.find(marker)
if idx < 0:
    print("[WARN] marker not found")
    sys.exit(0)

# End: next "\n## " after marker
end_marker = raw.find(b"\n## ", idx + len(marker))
if end_marker < 0:
    end_marker = len(raw)

clean = (
    "## \U0001F697 交通模式 / CSP Traffic Mode\r\n"
    "\r\n"
    "全部 13 個試場已加入 CSP Traffic mode 所需配置：\r\n"
    "\r\n"
    "- `data/traffic.json`：由每個試場嘅 AI spline + OSM 道路數據自動生成分段、雙向 traffic lanes 同路口（junctions；長跳點自動切段，路口只保留同 \u22652 條車道相交者）\r\n"
    "- `#traffic-planner-ready`：UI layout tag，令 CSP Traffic mode 顯示該試場\r\n"
    "- `[_SCRIPTING_PHYSICS] ALLOW_NEW_MODE_SCRIPTS=1`：允許 Traffic mode 修改物理\r\n"
    "- Traffic car 模型由 CSP Traffic Tool 管理；首次使用可讓 CSP 自動下載官方 traffic data\r\n"
    "\r\n"
    "### 使用 / Usage\r\n"
    "1. 開 AC \u2192 Practice \u2192 揀任何 `Hong Kong 1:1` 試場\r\n"
    "2. 選擇 CSP **Traffic** game mode（如未見到，先重啟 Content Manager）\r\n"
    "3. 設定交通密度（Traffic mode 預設最多 1,500 部）\r\n"
    "4. 開始後，車輛會沿試場 traffic lanes 行駛；已閉合路段會循環，開放路段會由 CSP graph 入口/出口管理\r\n"
    "\r\n"
    "### 重建交通配置 / Regenerate\r\n"
    "```powershell\r\n"
    "python tools/generate_traffic_json.py\r\n"
    "```\r\n"
    "\r\n"
    "> Traffic JSON 係由 OSM/AI spline 生成嘅分段雙向 traffic lanes + 自動路口；交通燈程序同進階車道連接，可再用 CSP Objects Inspector \u2192 Traffic Planner 編輯。\r\n"
).encode("utf-8")

new_raw = raw[:idx] + clean + raw[end_marker:]
p.write_bytes(new_raw)
print("[OK] README traffic section fixed")
