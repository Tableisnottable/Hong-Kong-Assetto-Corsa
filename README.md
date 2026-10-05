# Hong Kong Assetto Corsa (香港 Assetto Corsa 模擬地圖與車輛專案)

## 📌 專案簡介 / Project Overview
本專案旨在結合香港地理資訊地圖 (CSDI) 空間數據與 Blender 3D 自動化流程，為 Assetto Corsa 構建 1:1 高精確度的香港道路網絡及考車車輛模型。
This project integrates Hong Kong Common Spatial Data Infrastructure (CSDI) GIS datasets with an automated Blender pipeline to construct 1:1 scale Hong Kong road networks and driving test vehicles for Assetto Corsa.

## 🚗 目前進度與測試 / Current Focus & Progress
我們目前正在使用香港駕駛考試的實際路線與考車型號進行模擬測試：
We are currently conducting simulation testing with actual Hong Kong driving test routes and vehicles:
* **地圖製作 (Map Building)**：透過 CSDI 3D 視覺化數據、地形高程 (DTM) 與道路線條自動生成賽道模型 (.kn5)。
* **車輛模擬 (Car Modeling)**：涵蓋香港駕駛考試 1、1A、2、2A、17 及 17A 類別的標準考車型號規格與動態調校。
* **路面測試 (Road Testing)**：結合真實考車路線進行駕駛模擬與駕駛考試訓練。

## ⚙️ 自動化構建 / Automated Pipeline (v1)
所有的自動化構建腳本、設定模板及網頁界面均收錄於 uto/v1/ 目錄中：
All automation build scripts, configuration templates, and web interfaces are located in uto/v1/:
* uto/v1/build_and_deploy.ps1: 一鍵以管理員權限構建並部署 .kn5 到 Assetto Corsa。
* uto/v1/web/: 結合 CSDI 7 階段流程圖層的 Web Geoportal 界面與車輛規格頁面。

## Bus assets and ACROSS fleet catalog

The Hong Kong double-decker bus prototype is in `asset/vehicles/hk_double_decker_bus/`. The ACROSS catalog used for traffic planning is in `docs/across/`, including all listed model records and compact fleet/type code counts such as `E5T`, `E6X`, and `E6M`. Regenerate the catalog with:

```powershell
python .\tools\across_catalog.py --output .\build\across --cache .\build\across-cache
```

ACROSS counts may include historical, spare, training, or retired entries and are not claims about an operator's current active fleet.
