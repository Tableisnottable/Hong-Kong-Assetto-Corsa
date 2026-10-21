-- HK Exam Routes (auto-generated from asset/routes/all_road_test_routes.json)
-- Only centres with generated maps are included.

return {
  ["happy_valley_1"] = {
    centre = "happy_valley",
    name = "跑馬地路線一",
    steps = {
      { step = 1, instruction = "試場閘口駛出", turn = "R" },
      { step = 2, instruction = "右轉荷塘道", turn = "L" },
      { step = 3, instruction = "左轉成和道", turn = "L" },
      { step = 4, instruction = "左轉景光街", turn = "L" },
      { step = 5, instruction = "左轉山光道", turn = "L" },
      { step = 6, instruction = "左轉聚文街", turn = "R" },
      { step = 7, instruction = "右轉成和道", turn = "R" },
      { step = 8, instruction = "右轉冬青道", turn = "L" },
      { step = 9, instruction = "左轉荷塘道", turn = "FINISH" },
    },
  },

  ["happy_valley_2"] = {
    centre = "happy_valley",
    name = "跑馬地路線二",
    steps = {
      { step = 1, instruction = "試場閘口駛出", turn = "R" },
      { step = 2, instruction = "右轉荷塘道", turn = "R" },
      { step = 3, instruction = "右轉成和道", turn = "STRAIGHT" },
      { step = 4, instruction = "黃泥涌道方向", turn = "ROUNDABOUT" },
      { step = 5, instruction = "迴旋處", turn = "L" },
      { step = 6, instruction = "荷塘道", turn = "FINISH" },
    },
  },

  ["so_kun_po_1"] = {
    centre = "so_kun_po",
    name = "掃桿埔路線一",
    steps = {
      { step = 1, instruction = "試場斜路開車", turn = "SLOPE_START" },
      { step = 2, instruction = "三手軚掉頭", turn = "UTURN" },
      { step = 3, instruction = "倒後泊L位", turn = "REVERSE_L_PARK" },
      { step = 4, instruction = "沿大球場徑", turn = "STRAIGHT" },
      { step = 5, instruction = "左轉加路連山道", turn = "L" },
      { step = 6, instruction = "左轉禮頓道", turn = "L" },
      { step = 7, instruction = "左轉黃泥涌道", turn = "L" },
      { step = 8, instruction = "左轉樂活道", turn = "L" },
      { step = 9, instruction = "直去連道", turn = "STRAIGHT" },
      { step = 10, instruction = "返回試場", turn = "FINISH" },
    },
  },

  ["so_kun_po_2"] = {
    centre = "so_kun_po",
    name = "掃桿埔路線二",
    steps = {
      { step = 1, instruction = "試場斜路開車", turn = "SLOPE_START" },
      { step = 2, instruction = "三手軚掉頭", turn = "UTURN" },
      { step = 3, instruction = "倒後泊L位", turn = "REVERSE_L_PARK" },
      { step = 4, instruction = "沿大球場徑", turn = "STRAIGHT" },
      { step = 5, instruction = "樂活道方向", turn = "L" },
      { step = 6, instruction = "斜路上山", turn = "SLOPE_UP" },
      { step = 7, instruction = "返回試場", turn = "FINISH" },
    },
  },

  ["so_kun_po_3"] = {
    centre = "so_kun_po",
    name = "掃桿埔路線三",
    steps = {
      { step = 1, instruction = "試場斜路開車", turn = "SLOPE_START" },
      { step = 2, instruction = "三手軚掉頭", turn = "UTURN" },
      { step = 3, instruction = "倒後泊L位", turn = "REVERSE_L_PARK" },
      { step = 4, instruction = "經銅鑼灣道", turn = "STRAIGHT" },
      { step = 5, instruction = "禮頓道", turn = "L" },
      { step = 6, instruction = "返回試場", turn = "FINISH" },
    },
  },

  ["so_kun_po_4"] = {
    centre = "so_kun_po",
    name = "掃桿埔路線四",
    steps = {
      { step = 1, instruction = "試場斜路開車", turn = "SLOPE_START" },
      { step = 2, instruction = "三手軚掉頭", turn = "UTURN" },
      { step = 3, instruction = "倒後泊L位", turn = "REVERSE_L_PARK" },
      { step = 4, instruction = "加路連山道", turn = "STRAIGHT" },
      { step = 5, instruction = "禮頓道", turn = "L" },
      { step = 6, instruction = "黃泥涌道", turn = "L" },
      { step = 7, instruction = "返回試場", turn = "FINISH" },
    },
  },

  ["sheung_on_1"] = {
    centre = "sheung_on_street",
    name = "柴灣常安街路線一",
    steps = {
      { step = 1, instruction = "試埸開出", turn = "R" },
      { step = 2, instruction = "右轉常安街", turn = "L" },
      { step = 3, instruction = "左轉豐業街", turn = "R" },
      { step = 4, instruction = "右轉新業街", turn = "R" },
      { step = 5, instruction = "右轉柴灣道", turn = "L" },
      { step = 6, instruction = "左轉永平街", turn = "L" },
      { step = 7, instruction = "左轉新廈街", turn = "UTURN" },
      { step = 8, instruction = "上泳池掉頭", turn = "R" },
      { step = 9, instruction = "右轉永平街", turn = "L" },
      { step = 10, instruction = "左轉柴灣道", turn = "R" },
      { step = 11, instruction = "右轉怡順街", turn = "R" },
      { step = 12, instruction = "右轉怡豐街", turn = "R" },
      { step = 13, instruction = "右轉金源里", turn = "L" },
      { step = 14, instruction = "左轉柴灣道", turn = "L" },
      { step = 15, instruction = "左轉常安街", turn = "FINISH" },
    },
  },

  ["tin_kwong_1"] = {
    centre = "tin_kwong_road",
    name = "天光道路線一",
    steps = {
      { step = 1, instruction = "試埸開出", turn = "L" },
      { step = 2, instruction = "左轉天光道", turn = "R" },
      { step = 3, instruction = "右轉靠背窩道", turn = "L" },
      { step = 4, instruction = "左轉落山道", turn = "R" },
      { step = 5, instruction = "右轉美善同道", turn = "R" },
      { step = 6, instruction = "右轉靠江蘇街", turn = "R" },
      { step = 7, instruction = "右轉靠背窩道", turn = "L" },
      { step = 8, instruction = "左轉天光道", turn = "R" },
      { step = 9, instruction = "右轉常康街", turn = "UTURN" },
      { step = 10, instruction = "調頭操作", turn = "L" },
      { step = 11, instruction = "左轉常盛街", turn = "L" },
      { step = 12, instruction = "左轉天光道", turn = "R" },
    },
  },

  ["tin_kwong_2"] = {
    centre = "tin_kwong_road",
    name = "天光道路線二",
    steps = {
      { step = 1, instruction = "試埸開出", turn = "L" },
      { step = 2, instruction = "左轉天光道", turn = "R" },
      { step = 3, instruction = "右轉常盛街", turn = "R" },
      { step = 4, instruction = "右轉常康街", turn = "UTURN" },
      { step = 5, instruction = "調頭操作", turn = "L" },
      { step = 6, instruction = "左轉常盛街", turn = "R" },
      { step = 7, instruction = "右轉天光道", turn = "L" },
      { step = 8, instruction = "左轉馬頭圍道", turn = "L" },
      { step = 9, instruction = "左轉農圃道", turn = "R" },
      { step = 10, instruction = "右轉天光道", turn = "R" },
    },
  },

  ["tin_kwong_3"] = {
    centre = "tin_kwong_road",
    name = "天光道路線三",
    steps = {
      { step = 1, instruction = "試埸開出", turn = "R" },
      { step = 2, instruction = "右轉天光道", turn = "L" },
      { step = 3, instruction = "左轉亞皆老街", turn = "L" },
      { step = 4, instruction = "左轉嘉齡道", turn = "R" },
      { step = 5, instruction = "右轉巴富街", turn = "L" },
      { step = 6, instruction = "左轉石鼓街", turn = "L" },
      { step = 7, instruction = "左轉常盛街", turn = "R" },
      { step = 8, instruction = "右轉常康街", turn = "UTURN" },
      { step = 9, instruction = "調頭操作", turn = "L" },
      { step = 10, instruction = "左轉常盛街", turn = "L" },
      { step = 11, instruction = "左轉天光道", turn = "R" },
    },
  },

  ["yau_tong_1"] = {
    centre = "yau_tong",
    name = "油塘路線一",
    steps = {
      { step = 1, instruction = "試場開出", turn = "STRAIGHT" },
      { step = 2, instruction = "油塘工業區", turn = "ROUNDABOUT" },
      { step = 3, instruction = "迴旋處", turn = "FINISH" },
    },
  },

  ["yau_tong_2"] = {
    centre = "yau_tong",
    name = "油塘路線二",
    steps = {
      { step = 1, instruction = "試場開出", turn = "STRAIGHT" },
      { step = 2, instruction = "油塘工業區", turn = "SLOPE" },
      { step = 3, instruction = "上落斜", turn = "FINISH" },
    },
  },

  ["shek_am_1"] = {
    centre = "shek_am",
    name = "石蔭路線一",
    steps = {
      { step = 1, instruction = "試場開出", turn = "STRAIGHT" },
      { step = 2, instruction = "石蔭住宅區", turn = "L" },
      { step = 3, instruction = "梨木道", turn = "FINISH" },
    },
  },

  ["shek_am_2"] = {
    centre = "shek_am",
    name = "石蔭路線二",
    steps = {
      { step = 1, instruction = "試場開出", turn = "STRAIGHT" },
      { step = 2, instruction = "石蔭住宅區", turn = "ROUNDABOUT" },
      { step = 3, instruction = "迴旋處", turn = "FINISH" },
    },
  },

  ["texaco_1"] = {
    centre = "texaco_road",
    name = "荃灣德士古道路線一",
    steps = {
      { step = 1, instruction = "德士古道駕駛考試中心出發", turn = "STRAIGHT" },
      { step = 2, instruction = "德士古道近馬頭壩道駛出", turn = "ROUNDABOUT" },
      { step = 3, instruction = "德士古道主幹道", turn = "STRAIGHT" },
      { step = 4, instruction = "進入德士古道迴旋處（地獄迴旋處）", turn = "L" },
      { step = 5, instruction = "德士古道北", turn = "INDUSTRIAL" },
      { step = 6, instruction = "青山公路-荃灣段", turn = "UTURN" },
      { step = 7, instruction = "工業區（永德街、龍德街）", turn = "FINISH" },
    },
  },

  ["texaco_2"] = {
    centre = "texaco_road",
    name = "荃灣德士古道路線二",
    steps = {
      { step = 1, instruction = "德士古道駕駛考試中心出發", turn = "STRAIGHT" },
      { step = 2, instruction = "德士古道", turn = "L" },
      { step = 3, instruction = "沙咀道方向", turn = "INDUSTRIAL" },
      { step = 4, instruction = "荃灣工業區", turn = "ROUNDABOUT" },
      { step = 5, instruction = "迴旋處", turn = "FINISH" },
    },
  },

  ["texaco_3"] = {
    centre = "texaco_road",
    name = "荃灣德士古道路線三",
    steps = {
      { step = 1, instruction = "德士古道駕駛考試中心出發", turn = "STRAIGHT" },
      { step = 2, instruction = "德士古道", turn = "L" },
      { step = 3, instruction = "大窩口方向", turn = "STRAIGHT" },
      { step = 4, instruction = "荃灣路", turn = "ROUNDABOUT" },
      { step = 5, instruction = "迴旋處", turn = "FINISH" },
    },
  },

}
