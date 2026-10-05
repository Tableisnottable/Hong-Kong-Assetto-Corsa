# 香港 1:1 Assetto Corsa / Hong Kong 1:1 Assetto Corsa

香港本專案旨在製作一個完整的香港 1:1 Assetto Corsa 地圖，目標是將整個香港以真實尺度重建為可駕駛的虛擬環境，而不只是單一路線或單一地區。

This project aims to create a complete Hong Kong 1:1 map for Assetto Corsa. The goal is to rebuild the whole territory at real-world scale as a drivable virtual environment, not just a single route or a single area.

## 專案目的 / Project purpose

本專案以香港道路與路線資料為基礎，將地圖開發分為多個步驟逐步完成：先確認範圍，再整理資料，接著建立原型，最後驗證遊戲內表現與伺服器運作。

This project is based on Hong Kong road and route data, and the map is developed in stages: first define the scope, then gather reference data, build a prototype, and finally verify the in-game result and server setup.

## 專案流程 / Project process

1. 範圍確認 / Define the map scope
   - 確認要建立的地區與路線範圍。
   - 確認目標是全香港地圖，還是先以某一個區域作為原型測試。
   - 例如現階段先聚焦於 HP1C 圖幅與天光道考試路線。

   - Confirm the area and route coverage to be built.
   - Decide whether the goal is a full Hong Kong map or a smaller prototype area first.
   - For example, the current focus is on a specific HP1C sheet and the Tin Kwong Road driving-test routes.

2. 資料整理 / Collect and prepare reference data
   - 收集道路幾何、路線資訊、街道佈局與地形參考。
   - 以真實地理資料作為基礎，避免只依賴單一來源。
   - 將資料整理成適合地圖製作使用的範圍與分層。

   - Gather road geometry, route information, street layout, and terrain references.
   - Use real-world geographic data as the foundation rather than relying on a single source.
   - Organize the data into usable map areas and layers for production.

3. 原型建立 / Build the prototype
   - 建立路線範圍的初步地圖原型。
   - 先完成道路骨架與主要功能區域，再逐步補足細節。
   - 確認原型能正確反映道路走向與路線安排。

   - Create the initial map prototype for the selected area.
   - Build the road skeleton and essential layout first, then add details gradually.
   - Confirm that the prototype correctly reflects road direction and route layout.

4. 檢查與修正 / Review and refine
   - 檢查道路連接、車道方向、路口設計與整體地圖表現。
   - 根據實際資料做修正，避免路線與現實環境偏差過大。
   - 在進入正式輸出前，先完成 prototype 內部驗證。

   - Check road connectivity, lane direction, junction design, and overall map quality.
   - Correct discrepancies against the source data to keep the map realistic.
   - Complete internal review before final export and packaging.

5. 輸出與組裝 / Export and package
   - 將完成的區域整理成可供遊戲使用的地圖內容。
   - 按圖幅或區塊處理，保持清晰的分區與載入順序。
   - 準備地圖檔案與相關設定，供後續測試使用。

   - Export the completed area into game-ready map content.
   - Organize by tile or region to keep the map structure clear and manageable.
   - Prepare the map files and related configuration for testing.

6. 測試與發佈 / Test and release
   - 在 Assetto Corsa 中測試路線與地圖表現。
   - 檢查載入、視覺表現與伺服器運作是否正常。
   - 若結果符合要求，才進入後續擴展或正式發佈。

   - Test the route and map behavior in Assetto Corsa.
   - Check loading, visuals, and server performance.
   - Only continue to expansion or release after the result is stable and acceptable.

## 現階段重點 / Current focus

目前先從一個有限範圍的原型開始，重點是確認流程是否穩定、地圖資料是否可用，以及路線是否能在遊戲中正常呈現。

The current phase starts with a limited prototype so we can confirm the workflow is stable, the map data is usable, and the route can be presented correctly in-game.

## 資料來源 / Data sources

- 路線資料與轉向資訊來自香港考試路線參考。
- 地理資料與道路參考來自公開地圖與地理資料來源。
- 相關測量與圖幅資料用於控制區域邊界與地圖分區。

- Route and turning information comes from Hong Kong driving-route references.
- Geographic and road references come from public map and geospatial sources.
- Survey and sheet data are used to define region boundaries and map zoning.

## 結論 / Conclusion

這個專案的核心不是一次性完成整張香港地圖，而是先建立穩定的製作流程，再逐步擴大地圖範圍與路線覆蓋。

The core of this project is not to finish the whole Hong Kong map in one step, but to establish a stable production process and then expand the coverage gradually.
