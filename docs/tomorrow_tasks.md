# 聽日任務清單 / Tomorrow's Task List

> 準備日期：2026-10-13 | 所有前置資料已齊備並推送 ✅

## 1️⃣ ksEditor 轉 KN5（必須人手做，約 15-20 分鐘）

詳細步驟見 [docs/kseditor_conversion_guide.md](kseditor_conversion_guide.md)。

### 地圖 Maps (3)
| # | 試場 | FBX 來源 | 匯出目標 |
|---|---|---|---|
| 1 | 天光道 | `build/HP1C/tin_kwong_road/hd_map.fbx` (18MB) | `content/tracks/hong_kong_1to1/hd_map.kn5` |
| 2 | 柴灣 | `build/HP1C/sheung_on_street/hd_map.fbx` (7MB) | `content/tracks/hong_kong_1to1_sheung_on/hd_map.kn5` |
| 3 | 荃灣 | `build/HP1C/texaco_road/hd_map.fbx` (21MB) | `content/tracks/hong_kong_1to1_texaco/hd_map.kn5` |

### 車輛 Cars (6)
| # | 車輛 | FBX 來源 | 匯出目標 |
|---|---|---|---|
| 4 | Yaris (1) | `content/cars/hk_cat1_toyota_yaris/body.fbx` | `.../hk_cat1_toyota_yaris.kn5` |
| 5 | Prius (1A) | `content/cars/hk_cat1a_toyota_prius/body.fbx` | `.../hk_cat1a_toyota_prius.kn5` |
| 6 | HiAce MT (2) | `content/cars/hk_cat2_toyota_hiace_mt/body.fbx` | `.../hk_cat2_toyota_hiace_mt.kn5` |
| 7 | HiAce AT (2A) | `content/cars/hk_cat2a_toyota_hiace_at/body.fbx` | `.../hk_cat2a_toyota_hiace_at.kn5` |
| 8 | E500 Gen1 (17) | `content/cars/hk_cat17_adl_e500_gen1/body.fbx` | `.../hk_cat17_adl_e500_gen1.kn5` |
| 9 | E500 MMC (17A) | `content/cars/hk_cat17a_adl_e500_mmc/body.fbx` | `.../hk_cat17a_adl_e500_mmc.kn5` |

### 操作
1. `Set-Location "A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor"; .\ksEditor.exe`
2. File → Open → 選 FBX → 檢查 → File → Export → KN5
3. 每個 1-2 分鐘

## 2️⃣ 入 AC 實測

```powershell
# 複製賽道 + 車輛到 AC
Copy-Item content\tracks\hong_kong_1to1 "A:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\" -Recurse -Force
Copy-Item content\cars\hk_cat* "A:\SteamLibrary\steamapps\common\assettocorsa\content\cars\" -Recurse -Force
```

- 開 game 測試地圖行唔行得、車揸唔揸到
- 有問題調 `data/*.ini`（物理已齊，可直接改）

## 3️⃣ ACROSS 目錄用途（參考）

- `docs/across/across_bus_catalog.json` — 437 條巴士型號（KMB 96、Citybus 74...）
- `docs/across/across_fleet_summary.json` — 483 車隊記錄 + 數量
- E500/E500 MMC 規格已對照確認準確（KMB ATENU/E5T 876部、Citybus 12m/12.8m）
- 如需加交通巴士，可用 ACROSS 做選車參考

## 📦 已齊備的資料

| 項目 | 狀態 |
|---|---|
| 考車 6/6（data + ui + body + preview） | ✅ |
| 交通車 101/101 完整規格 | ✅ |
| 地圖 3 試場（extract + FBX + 預覽） | ✅ |
| 路試路線 13 試場 31 路線 | ✅ |
| 流水線工具 6/6 | ✅ |
| ksEditor 已安裝（A 盤） | ✅ |
| FBX 版本兼容（2014/2015） | ✅ |
