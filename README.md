# 香港天光道 Assetto Corsa Map Tools

這個 repository 是一個用來製作香港九龍天光道駕駛考試地圖的 Assetto Corsa project。The project currently provides a reproducible road blockout、route data、Blender generation scripts、FBX export helper，以及 Assetto Corsa track skeleton。

> **Current status / 目前狀態:** 目前輸出是可重建的 road blockout and project skeleton，不是完成品或可直接發布的 final KN5 track。A finished 1:1 map still requires original HP1C survey data、terrain、collision、AI lines、traffic assets and final ksEditor authoring。

## Project scope / 專案範圍

地圖以天光道考試路線為核心 / The map focuses on the Tin Kwong Road test routes；三條 route 共用同一個 shared road world，and overlapping roads are modeled only once：

1. **Route 1 / 路線一:** 天光道、背窩道、落山道、美善同道、江蘇街、常康街、常盛街及掉頭操作 / Tin Kwong Road, Back Cheung Road, Lok Shan Road, Mei Shing Tong Street, Jiangsu Street, Sheung Hong Street, Sheung Shing Street and the U-turn operation.
2. **Route 2 / 路線二:** 天光道、常盛街、常康街、馬頭圍道、農圃道及掉頭操作 / Tin Kwong Road, Sheung Shing Street, Sheung Hong Street, Ma Tau Wai Road, Farm Road and the U-turn operation.
3. **Route 3 / 路線三:** 天光道、亞皆老街、嘉齡道、巴富街、石鼓街、常盛街、常康街及掉頭操作 / Tin Kwong Road, Argyle Street, Carlisle Road, Pui Ching Road, Shek Ku Street, Sheung Shing Street, Sheung Hong Street and the U-turn operation.

完整中文 instructions 位於 `asset\routes\tin_kwong_road.json`，而 Blender generator 使用對應的 English road identifiers。

| Item / 項目 | Value / 值 |
| --- | --- |
| Map purpose / 用途 | 天光道駕駛考試路線 / Tin Kwong Road driving-test routes |
| Survey group / 資料圖組 | `HP1C` |
| Reference sheet / 參考圖幅 | `11-SW-9D` |
| Assetto Corsa map ID | `tin_kwong_road` |
| Road strategy / 道路策略 | One shared road world for all routes |
| Sheet strategy / 圖幅策略 | Follow original HP1C sheet boundaries |

HP1C 是 survey group and sheet identifier，不代表把整幅測量圖全部放入遊戲。The build should extract only the required driving-test road corridor，排除無關周邊區域。

## Repository structure / 目錄結構

```text
.
├── README.md
├── .gitignore
├── asset/
│   ├── routes/tin_kwong_road.json
│   ├── assetto_corsa/tin_kwong_road/
│   │   ├── models.ini
│   │   ├── data/surfaces.ini
│   │   ├── ui/ui_track.json
│   │   └── README.md
│   └── vehicles/hk_double_decker_bus/
├── auto/v1/                  # CSDI/Blender automation and web tools
├── build/HP1C/
│   ├── source/source_manifest.json
│   └── tin_kwong_road/
│       ├── routes.json
│       ├── tile_manifest.json
│       └── tin_kwong_road_blockout.blend
├── car/driving test car/     # Driving-test vehicle references
├── config/                   # Vehicle and map configuration
├── content/cars/             # Assetto Corsa car content
├── docs/                     # Production plans and ACROSS catalog
└── tools/
    ├── build_map.ps1
    ├── desktop_export.ps1
    ├── fetch_hk_data.py
    ├── across_catalog.py
    └── blender/
        ├── generate_tin_kwong.py
        └── export_tin_kwong_fbx.py
```

Downloader-generated `roads.osm.json` and `roads.geojson` are ignored by Git，因為它們可以重新下載；they remain locally under `build\HP1C\source\` as generator inputs。

## One-command build / 一鍵建圖

在 repository root 開啟 PowerShell / Open PowerShell at the repository root：

```powershell
.\tools\build_map.ps1
```

The pipeline 會執行以下步驟 / performs the following steps：

1. Run `tools\fetch_hk_data.py` and download nearby OSM roads through Overpass API。
2. Convert the response to GeoJSON，並使用 local cache。
3. Run `tools\blender\generate_tin_kwong.py` in Blender background mode。
4. Generate/update the `.blend` blockout、`routes.json` and `tile_manifest.json`。
5. Check Blender and ksEditor availability，並顯示 KN5 export 的下一步。

Known local installations / 已知本機安裝位置：

```text
C:\Program Files\Blender Foundation\Blender 5.1\blender.exe
A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe
```

`build_map.ps1` 會先 search `PATH`，找不到才使用 fallback paths；if your installation differs，請修改 `$blenderPath` and `$ksEditorPath`。

## Downloader safety / 下載器保護

`tools\fetch_hk_data.py` 對公開 API 採取 conservative request policy：

- At most one request at a time / 同一時間最多一個請求。
- Minimum 15-second interval / 新請求前至少等待 15 秒。
- Reuse local cache / 有效 `roads.osm.json` 時不重新下載。
- Maximum three retries with exponential backoff / 失敗時最多重試三次並逐步延遲。
- No parallel downloads、endpoint scanning or repeated bulk requests / 不使用並行下載、API 掃描或重複大量請求。
- 不會爬取 Google Maps tiles 或下載 Street View assets / Google Maps tiles and Street View assets are never scraped or downloaded。

如要強制重新下載，先確認 service terms and rate limits / confirm the service terms and rate limits first，再執行 / then run：

```powershell
Remove-Item .\build\HP1C\source\roads.osm.json
Remove-Item .\build\HP1C\source\roads.geojson
python .\tools\fetch_hk_data.py
```

## Data sources / 資料來源

| Source / 來源 | Purpose / 用途 | Usage / 使用方式 |
| --- | --- | --- |
| [TODS Kowloon routes](https://www.driving.com.hk/exam-routes-kowloon) | Route instructions and coordinate anchors | Reference only；頁面資料最後於 2021 年更新 |
| [GeoInfo Map](https://www.map.gov.hk/gm/) | Official Hong Kong map、roads、buildings and terrain reference | Official/manual reference |
| [eHongKongStreet](https://www.landsd.gov.hk/tc/resources/mapping-information/ehkg.html) | GeoPDF street maps and sheet calibration | Use original-size data for accurate calibration |
| [OpenStreetMap Overpass](https://overpass-api.de/) | Road centerlines and road names | Automated download；遵守 ODbL attribution |
| Google Maps | Current-condition comparison | Manual reference only；no scraping or asset extraction |

Before publishing a mod，請重新確認 official-data non-commercial terms、OSM attribution requirements and Google Maps terms。OSM blockout data is not a substitute for official HP1C survey geometry。

## Blender generator / Blender 生成器

可直接執行 / Run directly：

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  --python .\tools\blender\generate_tin_kwong.py
```

The generator 會清理 scene、讀取 `build\HP1C\source\roads.geojson`、將 WGS84 coordinates 轉成 local metre grid、建立 road strips and basic markings，然後輸出：

```text
build\HP1C\tin_kwong_road\tin_kwong_road_blockout.blend
build\HP1C\tin_kwong_road\routes.json
build\HP1C\tin_kwong_road\tile_manifest.json
```

如果 GeoJSON 不存在，generator 使用少量 built-in anchors 作 pipeline fallback / uses a small built-in anchor fallback；this fallback is for testing only，不代表完整或精確道路資料 / it is not a complete or accurate road dataset。

## FBX and KN5 export / 匯出流程

執行 / Run：

```powershell
.\tools\desktop_export.ps1
```

Helper 會檢查 `.blend`、Blender 和 official SDK ksEditor，要求使用者輸入 `EXPORT`，再輸出：

```text
build\HP1C\tin_kwong_road\11-SW-9D.fbx
```

之後會開啟 ksEditor / ksEditor will then open。User must load the FBX、檢查 materials/coordinates、再手動 export `11-SW-9D.kn5` / manually export the KN5；the helper does not use blind screen coordinates and will not overwrite existing output automatically。

## Assetto Corsa skeleton / AC 檔案骨架

Track skeleton 位於 `asset\assetto_corsa\tin_kwong_road\` / The track skeleton is located there：

- `models.ini` loads `11-SW-9D.kn5`。
- `data\surfaces.ini` contains initial `ROAD` and `GRASS` surfaces。
- `ui\ui_track.json` contains menu metadata。
- `README.md` explains installation and export notes。

### 2 GB sheet-splitting rule / 2 GB 分片規則

Treat 2 GB as the hard per-model limit，and 1.5 GB as the safety target：

- Under limit / 未超過：`11-SW-9D.kn5`
- Over limit / 超過：`11-SW-9D-1.kn5`、`11-SW-9D-2.kn5`
- More parts / 更多分片：`11-SW-9D-3.kn5`、`11-SW-9D-4.kn5`

Only oversized source sheets are split。分片應按同一 HP1C sheet 內的 actual road content 建立，不使用任意固定 100 x 100 metre grid，並保持 `tile_manifest.json` and `models.ini` 一致。

## Other repository projects / 其他專案內容

Repository 亦包含 broader Hong Kong Assetto Corsa work：

- `auto/v1/`: CSDI/Blender automation、vehicle data、templates and web pages / CSDI/Blender 自動化、車輛資料、模板和網頁。
- `asset/vehicles/hk_double_decker_bus/`: Hong Kong double-decker bus OBJ、MTL and manifest / 香港雙層巴士模型和 manifest。
- `car/driving test car/`: driving-test vehicle reference data / 駕駛考試車輛參考資料。
- `config/vehicles.json`: vehicle configuration index / 車輛設定索引。
- `docs/`: map-production plans and ACROSS fleet data / 地圖製作計劃和 ACROSS 車隊資料。
- `tools/across_catalog.py`: ACROSS fleet-catalog generator / ACROSS 車隊 catalog 生成器。

重新生成 ACROSS catalog / Regenerate the catalog：

```powershell
python .\tools\across_catalog.py --output .\build\across --cache .\build\across-cache
```

ACROSS counts may include historical、spare、training or retired vehicles，不能直接視為 operator current active fleet。

## Validation / 驗證

```powershell
python -m py_compile `
  .\tools\fetch_hk_data.py `
  .\tools\blender\generate_tin_kwong.py `
  .\tools\blender\export_tin_kwong_fbx.py

python -c "import json; json.load(open('asset/routes/tin_kwong_road.json', encoding='utf-8')); json.load(open('asset/assetto_corsa/tin_kwong_road/ui/ui_track.json', encoding='utf-8')); print('JSON valid')"

git diff --check
```

已驗證的項目包括 Python syntax、route/manifest JSON parsing、cached OSM download、Blender background generation、FBX export and ksEditor path detection / Validated items include all of these steps。

## Known limitations / 已知限制

正式完成地圖仍需要 / A finished map still requires：

- Original-size HP1C 11-SW-9D GeoPDF/GIS calibration。
- Correct Hong Kong 1980 Grid or survey-coordinate conversion。
- Elevation、contours and terrain meshes。
- Accurate road width、lane markings、curbs and junction geometry。
- Traffic lights、signs、guardrails、bus stops and roadside props。
- Buildings、distant scenery and collision meshes。
- Assetto Corsa AI lines、pits、spawns and timing lines。
- CSP/night lighting、reflection settings、final KN5 and in-game testing。

Current `.blend` is a development starting point，not a complete 1:1 Hong Kong driving-test map / 目前 `.blend` 只是開發起點，並非完整 1:1 香港考試地圖。

## Contribution workflow / 修改流程

1. Keep source URLs、download dates and license notes when changing data sources。
2. Avoid parallel or repeated requests to public APIs。
3. Model overlapping roads once，route differences go in route data。
4. Do not merge the full HP1C sheet or unrelated Hong Kong areas into one model。
5. Check every KN5 file size and apply the sheet naming rule。
6. Run Python、JSON and `git diff --check` validation after changes。

## License and disclaimer / 授權及免責

本 repository 的 scripts and configuration 是地圖製作工具，不會自動授予第三方 map data、government data、OSM data 或 Google Maps assets 的再發布權。Before publishing a mod，請遵守每個來源各自的 license、attribution、non-commercial and service-term requirements。
