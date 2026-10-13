# ksEditor KN5 轉換指南 / ksEditor KN5 Conversion Guide

所有 FBX 已驗證可直接用 ksEditor 開啟並轉換為 KN5。
All FBX files verified loadable in ksEditor for KN5 export.

## 環境 / Environment

- ksEditor: `A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe`
- FBX 版本: 2014/2015 (7400) — 與 ksEditor 內置 FBX SDK 2014.1 兼容 ✅
- 轉換方式: **人手 GUI 操作**（ksEditor 無 CLI/batch 模式）

## 轉換清單 / Conversion Checklist (9 個檔案)

### 地圖 Maps (3)

| # | 試場 | FBX 來源 | 匯出目標 | 大小 |
|---|---|---|---|---|
| 1 | 天光道 Tin Kwong | `build/HP1C/tin_kwong_road/hd_map.fbx` | `content/tracks/hong_kong_1to1/hd_map.kn5` | 18 MB |
| 2 | 柴灣 Sheung On | `build/HP1C/sheung_on_street/hd_map.fbx` | `content/tracks/hong_kong_1to1_sheung_on/hd_map.kn5` | 7 MB |
| 3 | 荃灣 Texaco | `build/HP1C/texaco_road/hd_map.fbx` | `content/tracks/hong_kong_1to1_texaco/hd_map.kn5` | 21 MB |

### 車輛 Cars (6)

| # | 車輛 | FBX 來源 | 匯出目標 | 大小 |
|---|---|---|---|---|
| 4 | Yaris (1) | `content/cars/hk_cat1_toyota_yaris/body.fbx` | `content/cars/hk_cat1_toyota_yaris/hk_cat1_toyota_yaris.kn5` | 23 KB |
| 5 | Prius (1A) | `content/cars/hk_cat1a_toyota_prius/body.fbx` | `content/cars/hk_cat1a_toyota_prius/hk_cat1a_toyota_prius.kn5` | 23 KB |
| 6 | HiAce MT (2) | `content/cars/hk_cat2_toyota_hiace_mt/body.fbx` | `content/cars/hk_cat2_toyota_hiace_mt/hk_cat2_toyota_hiace_mt.kn5` | 23 KB |
| 7 | HiAce AT (2A) | `content/cars/hk_cat2a_toyota_hiace_at/body.fbx` | `content/cars/hk_cat2a_toyota_hiace_at/hk_cat2a_toyota_hiace_at.kn5` | 23 KB |
| 8 | E500 Gen1 (17) | `content/cars/hk_cat17_adl_e500_gen1/body.fbx` | `content/cars/hk_cat17_adl_e500_gen1/hk_cat17_adl_e500_gen1.kn5` | 25 KB |
| 9 | E500 MMC (17A) | `content/cars/hk_cat17a_adl_e500_mmc/body.fbx` | `content/cars/hk_cat17a_adl_e500_mmc/hk_cat17a_adl_e500_mmc.kn5` | 25 KB |

## 操作步驟 / Steps (每個檔案)

1. 開啟 ksEditor（從佢自己目錄啟動）：
   ```powershell
   Set-Location "A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor"
   .\ksEditor.exe
   ```
2. File → Open → 選擇 FBX
3. 檢查模型顯示正常（材質：CAR_BODY / CAR_GLASS / CAR_WHEELS 或 1ROAD_ASPHALT 等）
4. File → Save / Export → 選擇 KN5 格式 → 存到上表「匯出目標」
5. 關閉，開下一個

**預計時間：每個 1-2 分鐘，總共約 15-20 分鐘。**

## 轉換後驗證 / Post-Conversion Check

```powershell
# KN5 檔案存在且非空
Get-ChildItem content\tracks\hong_kong_1to1\*.kn5, content\cars\*\*.kn5 |
  Select-Object Name, Length
```

## 安裝到 AC / Install to Assetto Corsa

```powershell
# 複製賽道
Copy-Item content\tracks\hong_kong_1to1 `
  "A:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\" -Recurse -Force

# 複製車輛 (6 部)
Copy-Item content\cars\hk_cat* `
  "A:\SteamLibrary\steamapps\common\assettocorsa\content\cars\" -Recurse -Force
```

## 已知限制 / Known Limitations

- ksEditor 無命令行模式（傳 FBX 參數會直接退出 rc=1）
- KN5IO/FBXImporter 為 internal C++ 類，無法用 .NET reflection 自動化
- ksEditor 內置 Python 3.3 只有標準庫，無場景 API
- 結論：人手 GUI 轉換 9 個檔案最快最可靠
