# 香港天光道 Assetto Corsa 地圖工具

這個 repository 是一個以**天光道駕駛考試路線**為目標的 Assetto Corsa 地圖製作起始專案。專案目前提供：

- 三條天光道考試路線的共用路線資料
- 基於 OpenStreetMap 道路資料的 Blender 程式化 blockout
- HP1C／11-SW-9D 測量圖幅識別及來源 manifest
- Assetto Corsa 的 `models.ini`、`surfaces.ini` 和 `ui_track.json` 骨架
- 單請求、低頻率、可快取的資料下載器
- Blender FBX 匯出工具
- 開啟官方 ksEditor 的桌面匯出輔助腳本

> **目前狀態：** 這是可重建的道路 blockout 和 Assetto Corsa 專案骨架，並不是已完成的公開發布版 KN5 賽道。正式地圖仍需要 HP1C 原尺寸測量資料、地形、碰撞、AI line、交通設施和最終 ksEditor 匯出。

## 專案目標

地圖以香港九龍天光道駕駛考試範圍為核心。三條路線共用同一個道路世界，避免為重疊道路重複建模：

1. **路線一**：天光道、背窩道、落山道、美善同道、江蘇街、常康街、常盛街及掉頭操作。
2. **路線二**：天光道、常盛街、常康街、馬頭圍道、農圃道及掉頭操作。
3. **路線三**：天光道、亞皆老街、嘉齡道、巴富街、石鼓街、常盛街、常康街及掉頭操作。

完整的中文轉向指令保存在 `asset\routes\tin_kwong_road.json`，Blender 生成器則使用對應的英文路段識別字串。

## 重要名稱和範圍

| 項目 | 值 |
| --- | --- |
| 地圖用途 | 天光道駕駛考試路線 |
| 資料圖組 | HP1C |
| 參考圖幅 | 11-SW-9D |
| Assetto Corsa 內部地圖 ID | `tin_kwong_road` |
| 道路模型策略 | 三條路線共用同一套道路 |
| 圖幅策略 | 按 HP1C 原圖幅邊界輸出 |
| 2 GB 策略 | 只有超過限制時才按同一圖幅分片 |

HP1C 是測量資料圖組／圖幅識別，不是把整幅測量圖全部放進遊戲。生成流程只應抽取考試路線所需的道路走廊，排除不需要的周邊區域。

## 目錄結構

```text
.
├── README.md
├── .gitignore
├── asset/
│   ├── routes/
│   │   └── tin_kwong_road.json
│   └── assetto_corsa/
│       └── tin_kwong_road/
│           ├── models.ini
│           ├── data/
│           │   └── surfaces.ini
│           ├── ui/
│           │   └── ui_track.json
│           └── README.md
├── build/
│   └── HP1C/
│       ├── source/
│       │   └── source_manifest.json
│       └── tin_kwong_road/
│           ├── routes.json
│           ├── tile_manifest.json
│           └── tin_kwong_road_blockout.blend
└── tools/
    ├── build_map.ps1
    ├── desktop_export.ps1
    ├── fetch_hk_data.py
    └── blender/
        ├── generate_tin_kwong.py
        └── export_tin_kwong_fbx.py
```

下載器產生的原始 `roads.osm.json` 和 `roads.geojson` 已加入 `.gitignore`，避免把可重新取得的大型原始資料重複提交到 Git。它們會保留在本機 `build\HP1C\source\` 作為生成輸入。

## 一鍵下載和生成

在 repository 根目錄以 PowerShell 執行：

```powershell
.\tools\build_map.ps1
```

流程如下：

1. 執行 `tools\fetch_hk_data.py`。
2. 從 Overpass API 取得天光道附近的 OSM 道路資料，並轉成 GeoJSON。
3. 使用本地快取，避免重複請求。
4. 使用 Blender 背景模式執行 `tools\blender\generate_tin_kwong.py`。
5. 產生或更新 `tin_kwong_road_blockout.blend`、`routes.json` 和 `tile_manifest.json`。
6. 檢查 Blender 和 ksEditor 是否可用，提示下一步 KN5 匯出。

目前已知的本機程式位置：

```text
Blender:
C:\Program Files\Blender Foundation\Blender 5.1\blender.exe

官方 Assetto Corsa SDK ksEditor:
A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe
```

`build_map.ps1` 會先嘗試從 `PATH` 找程式，找不到時再使用上述預設路徑。若你的安裝位置不同，請修改腳本中的 `$blenderPath` 和 `$ksEditorPath`，或把程式加入 `PATH`。

## 下載器的請求保護

`tools\fetch_hk_data.py` 有意避免對公開服務造成大量請求：

- 同一時間最多一個請求
- 新請求前至少等待 15 秒
- 已有有效 `roads.osm.json` 時直接使用本地快取
- 失敗時最多重試 3 次
- 重試使用指數退避及少量隨機延遲
- 不使用並行下載
- 不掃描 API endpoint
- 不下載 Google Maps 圖磚或 Street View 資產

如需要重新下載，先在確認服務條款和使用限制後刪除本機快取，再重新執行下載器：

```powershell
Remove-Item .\build\HP1C\source\roads.osm.json
Remove-Item .\build\HP1C\source\roads.geojson
python .\tools\fetch_hk_data.py
```

## 資料來源和授權注意事項

| 來源 | 用途 | 專案使用方式 |
| --- | --- | --- |
| [TODS 九龍考車路線](https://www.driving.com.hk/exam-routes-kowloon) | 路線轉向順序和頁面中的座標錨點 | 參考資料；頁面資料最後於 2021 年更新 |
| [GeoInfo Map](https://www.map.gov.hk/gm/) | 香港官方道路、建築、地形和位置參考 | 人工／官方資料參考 |
| [地政總署《e香港街》](https://www.landsd.gov.hk/tc/resources/mapping-information/ehkg.html) | GeoPDF 街道圖及圖幅校準 | 取得原尺寸資料後再作精確校準 |
| [OpenStreetMap Overpass](https://overpass-api.de/) | 道路中心線和道路名稱 | 自動下載；遵守 ODbL attribution |
| Google Maps | 現況人工比對 | 不爬取、不下載圖磚、不提取 Street View 資產 |

官方資料的非商業使用條款、OSM attribution 和 Google Maps 條款需要在公開發布 mod 前再次確認。現有生成器中的 OSM 資料不是 HP1C 正式測量資料的替代品。

## Blender 生成器

直接執行：

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  --python .\tools\blender\generate_tin_kwong.py
```

生成器的工作：

- 清除新 Blender 場景中的預設物件
- 讀取 `build\HP1C\source\roads.geojson`
- 將 WGS84 經緯度轉換成以考試中心為基準的本地米制座標
- 對 OSM 道路中心線做簡單曲線插值
- 生成道路 strip 和基本路面標線
- 將多條道路放在同一個共用道路世界
- 輸出 Blender `.blend`
- 輸出路線中心線和來源圖幅 manifest

如果 GeoJSON 不存在，生成器會使用內置的少量座標錨點作 fallback blockout。這個 fallback 只用於測試生成流程，不代表完整或精確的香港道路資料。

輸出位置：

```text
build\HP1C\tin_kwong_road\tin_kwong_road_blockout.blend
build\HP1C\tin_kwong_road\routes.json
build\HP1C\tin_kwong_road\tile_manifest.json
```

## FBX 和 KN5 匯出

Blender 本身可先輸出 FBX。執行：

```powershell
.\tools\desktop_export.ps1
```

腳本會：

1. 檢查 `.blend`、Blender 和官方 SDK ksEditor。
2. 要求使用者輸入 `EXPORT` 作明確確認。
3. 呼叫 `export_tin_kwong_fbx.py`，輸出：

   ```text
   build\HP1C\tin_kwong_road\11-SW-9D.fbx
   ```

4. 開啟 ksEditor。
5. 由使用者在 ksEditor 內載入 FBX，檢查模型、材質和座標，再手動輸出 KN5。

目前沒有使用盲目滑鼠座標，也不會自動覆蓋現有輸出。ksEditor 版本的可靠命令列匯出接口未確認，因此最後的 KN5 匯出保留在圖形介面中由使用者確認。

## Assetto Corsa 檔案骨架

Assetto Corsa 專案骨架位於：

```text
asset\assetto_corsa\tin_kwong_road\
```

### `models.ini`

預設載入：

```ini
[MODEL_0]
FILE=11-SW-9D.kn5
POSITION=0,0,0
ROTATION=0,0,0
```

如果同一個 HP1C 圖幅超過 2 GB，改成多個模型：

```ini
[MODEL_0]
FILE=11-SW-9D-1.kn5
POSITION=0,0,0
ROTATION=0,0,0

[MODEL_1]
FILE=11-SW-9D-2.kn5
POSITION=0,0,0
ROTATION=0,0,0
```

### `data\surfaces.ini`

目前提供最基本的 `ROAD` 和 `GRASS` surface 定義。正式版本應按 ksEditor 中的 material name、路面材質、碰撞需求和 Assetto Corsa 物理測試結果調整。

### `ui\ui_track.json`

提供選單名稱、描述、地區、標籤和 pitbox 數量。正式賽道完成後需要補上實際長度、預覽圖、起點和其他 UI 資料。

## 2 GB 圖幅分片規則

Assetto Corsa 單一模型檔按 2 GB 硬限制處理，生成策略使用 1.5 GB 作為安全目標。分片不是固定 100×100 米網格，而是以 HP1C 原圖幅為單位：

- 未超過限制：`11-SW-9D.kn5`
- 超過限制：`11-SW-9D-1.kn5`、`11-SW-9D-2.kn5`
- 需要更多分片時：`11-SW-9D-3.kn5`、`11-SW-9D-4.kn5`

只有超過限制的圖幅才會分片。分片應沿著同一 HP1C 圖幅內的實際道路內容建立，並在 `tile_manifest.json` 和 `models.ini` 保持一致。

## 測試和驗證

目前可使用以下命令驗證程式和資料：

```powershell
python -m py_compile `
  .\tools\fetch_hk_data.py `
  .\tools\blender\generate_tin_kwong.py `
  .\tools\blender\export_tin_kwong_fbx.py

python -c "import json; json.load(open('asset/routes/tin_kwong_road.json', encoding='utf-8')); json.load(open('asset/assetto_corsa/tin_kwong_road/ui/ui_track.json', encoding='utf-8')); print('JSON valid')"

git diff --check
```

已驗證的流程包括：

- Python 腳本語法檢查
- 路線、manifest 和 UI JSON 解析
- OSM 道路下載及快取路徑
- Blender 5.1 背景生成 `.blend`
- Blender FBX 匯出
- ksEditor 路徑檢查

## 目前未完成的部分

以下項目仍需要正式測量資料和 Assetto Corsa 資產製作：

- HP1C 11-SW-9D 原尺寸 GeoPDF／GIS 資料校準
- 正確的香港 1980 Grid 或其他測量坐標轉換
- 高程、等高線和地形網格
- 精確道路寬度、車道線、路緣和路口幾何
- 交通燈、路牌、欄杆、巴士站和路邊物件
- 建築物和遠景環境
- 道路碰撞網格
- Assetto Corsa AI line、pit、spawn 和 timing line
- CSP／夜間燈光和反射設定
- 最終 KN5、`models.ini`、`surfaces.ini` 和遊戲內測試
- 實際駕駛測試、性能測試和不同車種測試

因此，現有 `.blend` 可以作為開發起點，但不能宣稱已是完整 1:1 香港考試地圖。

## 參與和修改流程

1. 修改資料來源或生成器前，先保留來源 URL、下載日期和授權資訊。
2. 避免對公開 API 發送並行或重複請求。
3. 道路重疊部分只建立一次，路線差異放在路線資料中。
4. 不要將整幅 HP1C 或不需要的香港區域合併成單一模型。
5. 任何 KN5 輸出都要檢查檔案大小，並按圖幅規則命名。
6. 修改後執行 Python、JSON 和 `git diff --check` 驗證。

## 授權和免責

本 repository 的腳本和設定是地圖製作工具，不代表第三方地圖資料、政府資料、OSM 資料或 Google Maps 資產已自動授權重新發布。發布 mod 前，請分別遵守每個資料來源的授權、署名、非商業和服務條款要求。

## Repository 的其他內容

`origin/main` 同時包含較廣泛的香港 Assetto Corsa 模擬專案內容，不限於天光道地圖：

- `auto/v1/`：CSDI／Blender 自動化流程、車輛資料、模板和 web 介面。
- `auto/v1/cars/`：香港駕駛考試類別車輛的聲音來源及相關說明。
- `auto/v1/web/`：地圖與車輛資料展示頁面。
- `asset/vehicles/hk_double_decker_bus/`：香港雙層巴士 OBJ、MTL 和模型 manifest。
- `car/driving test car/`：駕駛考試車輛參考資料。
- `config/vehicles.json`：車輛設定索引。
- `docs/`：地圖製作、整體生產計劃及 ACROSS 車隊資料。
- `tools/across_catalog.py`：重建 ACROSS 車隊 catalog 的工具。

### ACROSS 車隊 catalog

ACROSS catalog 位於 `docs/across/`，包括車型記錄、車隊摘要和代碼統計。重新生成：

```powershell
python .\tools\across_catalog.py --output .\build\across --cache .\build\across-cache
```

ACROSS 統計可能包含歷史車輛、後備車、訓練車或已退役車輛，不應直接解讀為營運商目前的活躍車隊數量。

### CSDI／車輛自動化範圍

`auto/v1/` 是主分支上的較廣泛自動化版本，涵蓋 CSDI 資料處理、Blender 匯出、Assetto Corsa 模板、車輛資料和 web 介面。本 README 前面的 HP1C／天光道流程，是目前這個工作分支新增的道路 blockout pipeline；兩者可以並存，但不應把目前的 OSM blockout 宣稱為已完成的 CSDI 1:1 KN5。

---

# Hong Kong Tin Kwong Road Assetto Corsa Map Tools

This repository is a starting project for building an Assetto Corsa map based on the Tin Kwong Road driving-test routes in Kowloon, Hong Kong. It currently provides:

- Shared route data for the three Tin Kwong Road driving-test routes.
- A Blender procedural road blockout generated from OpenStreetMap road data.
- HP1C / 11-SW-9D survey-sheet identifiers and source manifests.
- Assetto Corsa `models.ini`, `surfaces.ini`, and `ui_track.json` templates.
- A cached, rate-limited data downloader.
- Blender FBX export tooling.
- A desktop helper for opening the official Assetto Corsa SDK ksEditor.

> **Current status:** This is a reproducible road blockout and Assetto Corsa project skeleton, not a finished public-release KN5 track. A final map still requires original HP1C survey data, terrain, collision meshes, AI lines, traffic assets, and final ksEditor export.

## Project scope

The map focuses on the Kowloon Tin Kwong Road driving-test area. All three routes share one road world so overlapping roads are modeled only once:

1. **Route 1:** Tin Kwong Road, Back Cheung Road, Lok Shan Road, Mei Shing Tong Street, Jiangsu Street, Sheung Hong Street, Sheung Shing Street, and the U-turn operation.
2. **Route 2:** Tin Kwong Road, Sheung Shing Street, Sheung Hong Street, Ma Tau Wai Road, Farm Road, and the U-turn operation.
3. **Route 3:** Tin Kwong Road, Argyle Street, Carlisle Road, Pui Ching Road, Shek Ku Street, Sheung Shing Street, Sheung Hong Street, and the U-turn operation.

The complete Chinese turn-by-turn instructions are stored in `asset\routes\tin_kwong_road.json`. The Blender generator uses corresponding English road identifiers.

## Names and geographic scope

| Item | Value |
| --- | --- |
| Map purpose | Tin Kwong Road driving-test routes |
| Survey group | HP1C |
| Reference sheet | 11-SW-9D |
| Assetto Corsa map ID | `tin_kwong_road` |
| Road strategy | One shared road world for all three routes |
| Sheet strategy | Export according to the original HP1C sheet boundary |
| 2 GB strategy | Split only when one source-sheet model exceeds the limit |

HP1C identifies the survey group and sheet. It does not mean that the complete source sheet is copied into the game. The build should extract only the road corridor required by the driving-test routes and exclude unrelated surrounding areas.

## Repository structure

```text
.
├── README.md
├── .gitignore
├── asset/
│   ├── routes/tin_kwong_road.json
│   └── assetto_corsa/tin_kwong_road/
│       ├── models.ini
│       ├── data/surfaces.ini
│       ├── ui/ui_track.json
│       └── README.md
├── build/HP1C/
│   ├── source/source_manifest.json
│   └── tin_kwong_road/
│       ├── routes.json
│       ├── tile_manifest.json
│       └── tin_kwong_road_blockout.blend
└── tools/
    ├── build_map.ps1
    ├── desktop_export.ps1
    ├── fetch_hk_data.py
    └── blender/
        ├── generate_tin_kwong.py
        └── export_tin_kwong_fbx.py
```

The downloader-generated `roads.osm.json` and `roads.geojson` files are ignored by Git because they can be downloaded again. They remain locally under `build\HP1C\source\` as generator inputs.

## One-command download and build

Run this from the repository root in PowerShell:

```powershell
.\tools\build_map.ps1
```

The pipeline:

1. Runs `tools\fetch_hk_data.py`.
2. Downloads nearby OSM roads through the Overpass API and converts them to GeoJSON.
3. Uses the local cache to avoid repeated requests.
4. Runs `tools\blender\generate_tin_kwong.py` in Blender background mode.
5. Generates or updates the Blender blockout, route data, and sheet manifest.
6. Checks whether Blender and ksEditor are available and reports the next KN5 step.

Known local installation paths:

```text
Blender:
C:\Program Files\Blender Foundation\Blender 5.1\blender.exe

Official Assetto Corsa SDK ksEditor:
A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe
```

`build_map.ps1` first searches `PATH`, then falls back to these paths. Update `$blenderPath` and `$ksEditorPath` if your installation differs.

## Downloader request protection

`tools\fetch_hk_data.py` is deliberately conservative:

- At most one request at a time.
- At least 15 seconds before a new request.
- Local cache reuse when `roads.osm.json` is available.
- At most three retries after failure.
- Exponential backoff with a small random delay.
- No parallel downloads.
- No endpoint scanning.
- No Google Maps tiles or Street View asset downloads.

To force a fresh download, first confirm the service terms and limits, then remove the local cache:

```powershell
Remove-Item .\build\HP1C\source\roads.osm.json
Remove-Item .\build\HP1C\source\roads.geojson
python .\tools\fetch_hk_data.py
```

## Data sources and licensing

| Source | Purpose | Project usage |
| --- | --- | --- |
| [TODS Kowloon driving routes](https://www.driving.com.hk/exam-routes-kowloon) | Route instructions and published coordinate anchors | Reference only; page data was last updated in 2021 |
| [GeoInfo Map](https://www.map.gov.hk/gm/) | Official Hong Kong roads, buildings, terrain, and location reference | Manual and official-data reference |
| [Lands Department eHongKongStreet](https://www.landsd.gov.hk/tc/resources/mapping-information/ehkg.html) | GeoPDF street maps and sheet calibration | Use original-size data for accurate calibration |
| [OpenStreetMap Overpass](https://overpass-api.de/) | Road centerlines and road names | Automated download; comply with ODbL attribution |
| Google Maps | Manual current-condition comparison | No scraping, tile downloading, or Street View asset extraction |

Before publishing a mod, re-check the non-commercial terms for official data, OSM attribution requirements, and Google Maps terms. OSM data in the current generator is not a replacement for official HP1C survey geometry.

## Blender generator

Run directly:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  --python .\tools\blender\generate_tin_kwong.py
```

The generator:

- Clears the default Blender scene.
- Reads `build\HP1C\source\roads.geojson`.
- Converts WGS84 coordinates into a local metre grid around the test centre.
- Applies simple curve interpolation to road centerlines.
- Creates road strips and basic road markings.
- Places all roads in one shared road world.
- Writes a Blender `.blend`.
- Writes route centerline data and source-sheet metadata.

If GeoJSON is missing, the generator uses a small built-in anchor fallback for pipeline testing only. That fallback is not a complete or accurate Hong Kong road dataset.

Generated files:

```text
build\HP1C\tin_kwong_road\tin_kwong_road_blockout.blend
build\HP1C\tin_kwong_road\routes.json
build\HP1C\tin_kwong_road\tile_manifest.json
```

## FBX and KN5 export

Blender can export the intermediate FBX with:

```powershell
.\tools\desktop_export.ps1
```

The helper:

1. Checks the `.blend`, Blender, and the official SDK ksEditor.
2. Requires the user to type `EXPORT`.
3. Exports:

   ```text
   build\HP1C\tin_kwong_road\11-SW-9D.fbx
   ```

4. Opens ksEditor.
5. Leaves the user to load the FBX, inspect materials and coordinates, and confirm the KN5 export.

The helper does not use blind screen coordinates and does not overwrite existing output automatically. A reliable ksEditor command-line export interface has not been confirmed, so final KN5 export remains an explicit GUI step.

## Assetto Corsa file skeleton

The track skeleton is under:

```text
asset\assetto_corsa\tin_kwong_road\
```

`models.ini` loads `11-SW-9D.kn5` by default. If the source-sheet model exceeds 2 GB, replace it with ordered parts such as `11-SW-9D-1.kn5` and `11-SW-9D-2.kn5`. `data\surfaces.ini` contains initial `ROAD` and `GRASS` surfaces, while `ui\ui_track.json` contains menu metadata.

## 2 GB sheet-splitting rule

Treat 2 GB as the hard per-model limit and 1.5 GB as the safety target:

- Under the limit: `11-SW-9D.kn5`
- Over the limit: `11-SW-9D-1.kn5`, `11-SW-9D-2.kn5`
- Additional parts: `11-SW-9D-3.kn5`, `11-SW-9D-4.kn5`

Only oversized source sheets are split. Splits should follow actual road content within the same HP1C sheet, not an arbitrary fixed 100 x 100 metre grid. Keep `tile_manifest.json` and `models.ini` consistent.

## Other repository projects

The repository also contains broader Hong Kong Assetto Corsa work beyond the Tin Kwong Road map:

- `auto/v1/`: CSDI/Blender automation, vehicle data, templates, and web pages.
- `auto/v1/cars/`: sound-source documentation for Hong Kong driving-test vehicle categories.
- `auto/v1/web/`: map and vehicle data pages.
- `asset/vehicles/hk_double_decker_bus/`: Hong Kong double-decker bus OBJ, MTL, and manifest.
- `car/driving test car/`: driving-test vehicle reference data.
- `config/vehicles.json`: vehicle configuration index.
- `docs/`: map-production plans and ACROSS fleet data.
- `tools/across_catalog.py`: ACROSS fleet-catalog generator.

Regenerate the ACROSS catalog with:

```powershell
python .\tools\across_catalog.py --output .\build\across --cache .\build\across-cache
```

ACROSS counts may include historical, spare, training, or retired vehicles and are not claims about an operator's current active fleet.

## Validation

Run:

```powershell
python -m py_compile `
  .\tools\fetch_hk_data.py `
  .\tools\blender\generate_tin_kwong.py `
  .\tools\blender\export_tin_kwong_fbx.py

python -c "import json; json.load(open('asset/routes/tin_kwong_road.json', encoding='utf-8')); json.load(open('asset/assetto_corsa/tin_kwong_road/ui/ui_track.json', encoding='utf-8')); print('JSON valid')"

git diff --check
```

Validated parts include Python syntax, route and manifest JSON parsing, cached OSM downloads, Blender background generation, Blender FBX export, and ksEditor path detection.

## Known limitations

The following still require official survey data and final Assetto Corsa authoring:

- HP1C 11-SW-9D original-size GeoPDF/GIS calibration.
- Correct Hong Kong 1980 Grid or other survey-coordinate conversion.
- Elevation, contours, and terrain meshes.
- Accurate road width, lane markings, curbs, and junction geometry.
- Traffic lights, signs, guardrails, bus stops, and roadside props.
- Buildings and distant scenery.
- Collision meshes.
- Assetto Corsa AI lines, pits, spawns, and timing lines.
- CSP/night lighting and reflection settings.
- Final KN5, physics tuning, in-game testing, and performance testing.

The current `.blend` is a development starting point and must not be described as a complete 1:1 Hong Kong driving-test map.

## Contribution workflow

1. Keep source URLs, download dates, and license notes when changing data sources or generators.
2. Avoid parallel or repeated requests to public APIs.
3. Model overlapping roads once and keep route differences in route data.
4. Do not merge the full HP1C sheet or unrelated Hong Kong areas into one model.
5. Check every KN5 output size and apply the sheet naming rule.
6. Run Python, JSON, and `git diff --check` validation after changes.

## License and disclaimer

The scripts and configuration in this repository are map-production tools. They do not automatically grant redistribution rights for third-party map data, government data, OSM data, or Google Maps assets. Before publishing a mod, follow the separate license, attribution, non-commercial, and service-term requirements for every source.
