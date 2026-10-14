# 今日工作計劃 / Today's Task Plan (2026-10-14)

> 早晨！今日目標：**將地圖 + 考車放入 Assetto Corsa 實測** 🏁

## 1️⃣ 轉換 KN5（9 個檔案）

### 自動化（先試）
```powershell
# 喺互動桌面運行（唔係遠端/SSH）
python tools\auto_kn5_convert.py yaris     # 先試一部車
python tools\auto_kn5_convert.py           # 成功就轉埋其餘
```

**⚠️ 已知狀態（2026-10-14 測試）：**
- ✅ ksEditor 啟動 + File 菜單 invoke 成功
- ✅ Open FBX menu item 搵到 + invoke 成功
- ❌ Open 對話框喺非互動 session 係 hidden（visible=False）
- ❌ Win32 menu_select 唔適用（WinForms 自訂菜單）
- ➡️ **需要喺真正互動桌面運行**（你坐喺部機前面時）

### 手動（自動化唔得時）
1. `Set-Location "A:\SteamLibrary\steamapps\common\assettocorsa\sdk\editor"; .\ksEditor.exe`
2. File → Open FBX → 揀 `content\cars\hk_cat1_toyota_yaris\body.fbx`
3. File → Save KN5 → Car → 存做 `content\cars\hk_cat1_toyota_yaris\hk_cat1_toyota_yaris.kn5`
4. 重複 6 部車 + 3 個地圖（地圖用 Track 模式）

| # | 類型 | FBX | 目標 KN5 |
|---|---|---|---|
| 1-3 | 地圖 | `build/HP1C/*/hd_map.fbx` | `content/tracks/*/hd_map.kn5` |
| 4-9 | 車 | `content/cars/*/body.fbx` | `content/cars/*/<id>.kn5` |

## 2️⃣ 安裝到 AC

```powershell
Copy-Item content\tracks\hong_kong_1to1* "A:\SteamLibrary\steamapps\common\assettocorsa\content\tracks\" -Recurse -Force
Copy-Item content\cars\hk_cat* "A:\SteamLibrary\steamapps\common\assettocorsa\content\cars\" -Recurse -Force
```

## 3️⃣ 實測

- 開 Assetto Corsa → 揀 `hong_kong_1to1` 地圖
- 揀考車（Yaris / HiAce / E500）
- 試揸：天光道路線一（已內置 AI 路線 61,540 節點）
- 檢查：物理手感、AI 車、地圖碰撞

## 4️⃣ 有問題就調

- 物理：`content/cars/*/data/*.ini`
- 地圖：重新生成 FBX → 再轉 KN5
- AI：`python tools\generate_ai_spline.py` 再生成

## ✅ 已完成嘅準備

- [x] 9 個 FBX（3 地圖 + 6 車）
- [x] AI 路線（3 試場，V7 格式已驗證）
- [x] 物理 data（6 車 6/6）
- [x] 賽道 config（models.ini / surfaces.ini / ui_track.json）
- [x] 自動化腳本（pywinauto 已裝）
- [x] ksEditor 位置確認（A 盤）
