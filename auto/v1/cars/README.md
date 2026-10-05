# Hong Kong Assetto Corsa - Vehicle Mod Requirements (車輛 Mod 架構指南)

本目錄包含香港駕駛考試 6 款類別車輛 (1, 1A, 2, 2A, 17, 17A) 在 Assetto Corsa 中運行所需的完整目錄架構。

---

## 📂 完整車輛 Mod 目錄結構 (Full Car Directory Layout)

```text
auto/v1/cars/hk_cat1_yaris_manual/
├── car.kn5                    # [必要] 3D 模型檔 (包含車身、車輪、車廂、錶板)
├── animations/                # [選填] 動態動畫
│   ├── wiper.ksanim           # 雨刮動畫
│   └── steer.ksanim           # 方向盤轉動動畫
├── data/                      # [必要] 物理數據檔
│   ├── car.ini                # 車重、軸距、轉向鎖定
│   ├── engine.ini             # 引擎馬力/扭力曲線
│   ├── drivetrain.ini         # 波箱齒比、傳動
│   ├── suspension.ini         # 懸掛幾何與避震
│   ├── tyres.ini              # 輪胎抓地力與尺寸
│   ├── brakes.ini             # 煞車力道與前後分配
│   ├── lights.ini             # 頭尾燈/方向燈光束與位置
│   └── analog_instruments.ini # 實體儀表板指針位置
├── sfx/                       # [必要] 引擎與環境聲音
│   ├── GUIDs.txt              # FMOD 聲音對應表
│   └── hk_cat1_yaris.bank     # FMOD 引擎聲浪與音效檔
├── skins/                     # [必要] 車身塗裝
│   └── default/
│       ├── body.dds           # 車身貼圖 (考車車身標示)
│       └── plate.dds          # 香港車牌貼圖
└── ui/                        # [必要] 選車界面資訊
    ├── ui_car.json            # 車輛規格描述 (馬力、年代、國家)
    ├── badge.png              # 品牌 Logo (如 Toyota / ADL)
    └── preview.png            # 選車畫面預覽圖 (1024x576)





