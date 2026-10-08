# 香港全境 1:1 真實道路 Assetto Corsa Map Tools

這個 repository 是一個用來製作 1:1 香港全境真實道路與真實駕駛環境的 Assetto Corsa project。The project currently provides reproducible 1:1 real road data、route data、Blender generation scripts、FBX export helper，以及 Assetto Corsa track skeleton。

> **Current status / 目前狀態:** 目前輸出是可重建的 1:1 全境真實道路 blockout and project skeleton，不是完成品或可直接發布的 final KN5 track。A finished 1:1 real-world map still requires survey data、terrain、collision、AI lines、traffic assets and final ksEditor authoring。

## Project scope / 專案範圍

地圖涵蓋 1:1 香港全境真實道路 / The map focuses on full Hong Kong real-world roads；各區共用同一個 shared road world，完全依據現實地理數據建置：

1. **Hong Kong Island / 香港島:** 港島核心區、主要幹道及山頂真實道路。
2. **Kowloon / 九龍:** 九龍各主要幹道、考試路線及市區真實街道網。
3. **New Territories / 新界:** 新界公路、鄉郊快道及真實山區公路。

完整中文 instructions 位於 `asset\routes\full_hk.json`，而 Blender generator 使用對應的 English road identifiers。

| Item / 項目 | Value / 值 |
| --- | --- |
| Map purpose / 用途 | 1:1 香港全境真實道路駕駛與模擬 / 1:1 Full Hong Kong real-world driving routes |
| Survey group / 資料圖組 | 全香港真實測量數據 / Full Hong Kong real survey data |
| Reference sheet / 參考圖幅 | `HK-FULL` |
| Assetto Corsa map ID | `full_hk` |
| Road strategy / 道路策略 | One shared road world based strictly on real-world GIS and OSM data |
| Sheet strategy / 圖幅策略 | Follow full Hong Kong boundaries |

全香港真實測量數據配合 1:1 高精度縮放，提供真實沉浸式模擬體驗。

## Repository structure / 目錄結構

```text
.
├── README.md
├── .gitignore
├── asset/
│   ├── routes/full_hk.json
│   ├── assetto_corsa/full_hk/
│   │   ├── models.ini
│   │   ├── data/surfaces.ini
│   │   ├── ui/ui_track.json
│   │   └── README.md
│   └── vehicles/hk_double_decker_bus/
├── auto/v1/                  # CSDI/Blender automation and web tools
├── build/HK_FULL/
│   ├── source/source_manifest.json
│   └── full_hk/
│       ├── routes.json
│       ├── tile_manifest.json
│       └── full_hk_blockout.blend
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
        ├── generate_full_hk.py
        └── export_full_hk_fbx.py

Downloader-generated roads.osm.json and roads.geojson are ignored by Git，因為它們可以重新下載；they remain locally under build\HK_FULL\source\ as generator inputs。
One-command build / 一鍵建圖
在 repository root 開啟 PowerShell / Open PowerShell at the repository root：
.\tools\build_map.ps1

The pipeline 會執行以下步驟 / performs the following steps：
 * Run tools\fetch_hk_data.py and download nearby OSM roads through Overpass API。
 * Convert the response to GeoJSON，並使用 local cache。
 * Run tools\blender\generate_full_hk.py in Blender background mode。
 * Generate/update the .blend blockout、routes.json and tile_manifest.json。
 * Check Blender and ksEditor availability，並顯示 KN5 export 的下一步。
Known local installations / 已知本機安裝位置：
C:\Program Files\Blender Foundation\Blender 5.1\blender.exe
A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor\ksEditor.exe

build_map.ps1 會先 search PATH，找不到才使用 fallback paths；if your installation differs，請修改 $blenderPath and $ksEditorPath。
Downloader safety / 下載器保護
tools\fetch_hk_data.py 對公開 API 採取 conservative request policy：
 * At most one request at a time / 同一時間最多一個請求。
 * Minimum 15-second interval / 新請求前至少等待 15 秒。
 * Reuse local cache / 有效 roads.osm.json 時不重新下載。
 * Maximum three retries with exponential backoff / 失敗時最多重試三次並逐步延遲。
 * No parallel downloads、endpoint scanning or repeated bulk requests / 不使用並行下載、API 掃描或重複大量請求。
 * 不會爬取 Google Maps tiles 或下載 Street View assets / Google Maps tiles and Street View assets are never scraped or downloaded。
如要強制重新下載，先確認 service terms and rate limits / confirm the service terms and rate limits first，再執行 / then run：
Remove-Item .\build\HK_FULL\source\roads.osm.json
Remove-Item .\build\HK_FULL\source\roads.geojson
python .\tools\fetch_hk_data.py

Data sources / 資料來源
| Source / 來源 | Purpose / 用途 | Usage / 使用方式 |
|---|---|---|
| GeoInfo Map | Official Hong Kong map、roads、buildings and terrain reference | Official/manual reference |
| eHongKongStreet | GeoPDF street maps and sheet calibration | Use original-size data for accurate calibration |
| OpenStreetMap Overpass | Real road centerlines and road names | Automated download；遵守 ODbL attribution |
| Google Maps | Current-condition comparison | Manual reference only；no scraping or asset extraction |
Before publishing a mod，請重新確認 official-data non-commercial terms、OSM attribution requirements and Google Maps terms。OSM blockout data is not a substitute for official survey geometry。
Blender generator / Blender 生成器
可直接執行 / Run directly：
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  --background `
  --python .\tools\blender\generate_full_hk.py

The generator 會清理 scene、讀取 build\HK_FULL\source\roads.geojson、將 WGS84 coordinates 轉成 local metre grid、建立真實 1:1 road strips and basic markings，然後輸出：
build\HK_FULL\full_hk\full_hk_blockout.blend
build\HK_FULL\full_hk\routes.json
build\HK_FULL\full_hk\tile_manifest.json

如果 GeoJSON 不存在，generator 使用少量 built-in anchors 作 pipeline fallback / uses a small built-in anchor fallback；this fallback is for testing only，不代表完整或精確道路資料 / it is not a complete or accurate road dataset。
FBX and KN5 export / 匯出流程
執行 / Run：
.\tools\desktop_export.ps1

Helper 會檢查 .blend、Blender 和 official SDK ksEditor，要求使用者輸入 EXPORT，再輸出：
build\HK_FULL\full_hk\full_hk.fbx

之後會開啟 ksEditor / ksEditor will then open。User must load the FBX、檢查 materials/coordinates、再手動 export full_hk.kn5 / manually export the KN5；the helper does not use blind screen coordinates and will not overwrite existing output automatically。
Assetto Corsa skeleton / AC 檔案骨架
Track skeleton 位於 asset\assetto_corsa\full_hk\ / The track skeleton is located there：
 * models.ini loads full_hk.kn5。
 * data\surfaces.ini contains initial ROAD and GRASS surfaces。
 * ui\ui_track.json contains menu metadata。
 * README.md explains installation and export notes。
2 GB sheet-splitting rule / 2 GB 分片規則
Treat 2 GB as the hard per-model limit，and 1.5 GB as the safety target：
 * Under limit / 未超過：full_hk.kn5
 * Over limit / 超過：full_hk-1.kn5、full_hk-2.kn5
 * More parts / 更多分片：full_hk-3.kn5、full_hk-4.kn5
Only oversized source sheets are split。分片應按同一 region 內的 actual real road content 建立，不使用任意固定 100 x 100 metre grid，並保持 tile_manifest.json and models.ini 一致。
Other repository projects / 其他專案內容
Repository 亦包含 broader Hong Kong Assetto Corsa work：
 * auto/v1/: CSDI/Blender automation、vehicle data、templates and web pages / CSDI/Blender 自動化、車輛資料、模板和網頁。
 * asset/vehicles/hk_double_decker_bus/: Hong Kong double-decker bus OBJ、MTL and manifest / 香港雙層巴士模型和 manifest。
 * car/driving test car/: driving-test vehicle reference data / 駕駛考試車輛參考資料。
 * config/vehicles.json: vehicle configuration index / 車輛設定索引。
 * docs/: map-production plans and ACROSS fleet data / 地圖製作計劃和 ACROSS 車隊資料。
 * tools/across_catalog.py: ACROSS fleet-catalog generator / ACROSS 車隊 catalog 生成器。
重新生成 ACROSS catalog / Regenerate the catalog：
python .\tools\across_catalog.py --output .\build\across --cache .\build\across-cache

ACROSS counts may include historical、spare、training or retired vehicles，不能直接視為 operator current active fleet。
Validation / 驗證
python -m py_compile `
  .\tools\fetch_hk_data.py `
  .\tools\blender\generate_full_hk.py `
  .\tools\blender\export_full_hk_fbx.py

python -c "import json; json.load(open('asset/routes/full_hk.json', encoding='utf-8')); json.load(open('asset/assetto_corsa/full_hk/ui/ui_track.json', encoding='utf-8')); print('JSON valid')"

git diff --check

已驗證的項目包括 Python syntax、route/manifest JSON parsing、cached OSM download、Blender background generation、FBX export and ksEditor path detection / Validated items include all of these steps。
Known limitations / 已知限制
正式完成 1:1 全境真實地圖仍需要 / A finished real-world map still requires：
 * Full-size Hong Kong GIS calibration。
 * Correct Hong Kong 1980 Grid or survey-coordinate conversion。
 * Elevation、contours and terrain meshes。
 * Accurate road width、lane markings、curbs and junction geometry。
 * Traffic lights、signs、guardrails、bus stops and roadside props。
 * Buildings、distant scenery and collision meshes。
 * Assetto Corsa AI lines、pits、spawns and timing lines。
 * CSP/night lighting、reflection settings、final KN5 and in-game testing。
Current .blend is a development starting point for a 1:1 full Hong Kong real-world simulation，not a complete map / 目前 .blend 只是 1:1 全境真實模擬的開發起點，並非完整地圖。
Contribution workflow / 修改流程
 * Keep source URLs、download dates and license notes when changing data sources。
 * Avoid parallel or repeated requests to public APIs。
 * Model overlapping real roads once。
 * Do not merge unrelated Hong Kong areas into one oversized model without splitting。
 * Check every KN5 file size and apply the sheet naming rule。
 * Run Python、JSON and git diff --check validation after changes。
License and disclaimer / 授權及免責
本 repository 的 scripts and configuration 是地圖製作工具，不會自動授予第三方 map data、government data、OSM data 或 Google Maps assets 的再發布權。Before publishing a mod，請遵守每個來源各自的 license、attribution、non-commercial and service-term requirements。

