-- HK Exam Routes Database (Auto-generated)
-- Simplified format for AC Lua

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

  ["chung_ngai_1"] = {
    centre = "chung_ngai_street",
    name = "忠義街路線一（私家車）",
    steps = {
      { step = 1, instruction = "試場駛出", turn = "S_PARK" },
      { step = 2, instruction = "考泊位S位", turn = "STRAIGHT" },
      { step = 3, instruction = "沿忠義街", turn = "R" },
      { step = 4, instruction = "右轉孝民街", turn = "R" },
      { step = 5, instruction = "右轉忠孝街", turn = "R" },
      { step = 6, instruction = "右轉佛光街", turn = "R" },
      { step = 7, instruction = "右轉忠孝街", turn = "R" },
      { step = 8, instruction = "右轉孝民街", turn = "FINISH" },
    },
  },

  ["chung_ngai_2"] = {
    centre = "chung_ngai_street",
    name = "忠義街路線二",
    steps = {
      { step = 1, instruction = "試場駛出", turn = "S_PARK" },
      { step = 2, instruction = "考泊位S位", turn = "STRAIGHT" },
      { step = 3, instruction = "忠義街", turn = "L" },
      { step = 4, instruction = "佛光街方向", turn = "ROUNDABOUT" },
      { step = 5, instruction = "迴旋處", turn = "FINISH" },
    },
  },

  ["pui_ching_1"] = {
    centre = "pui_ching_road",
    name = "培正道路線一",
    steps = {
      { step = 1, instruction = "試場", turn = "L" },
      { step = 2, instruction = "左轉培正道", turn = "STRAIGHT" },
      { step = 3, instruction = "直上常興街", turn = "L" },
      { step = 4, instruction = "左轉常盛街", turn = "L" },
      { step = 5, instruction = "左轉石鼓街", turn = "L" },
      { step = 6, instruction = "左轉巴富街", turn = "R" },
      { step = 7, instruction = "右轉公主道", turn = "L" },
      { step = 8, instruction = "左轉亞皆老街", turn = "L" },
      { step = 9, instruction = "左轉窩打老道", turn = "L" },
      { step = 10, instruction = "左轉培正道", turn = "SLOPE_START" },
      { step = 11, instruction = "文福道斜路開車", turn = "R" },
      { step = 12, instruction = "右轉文運道", turn = "L" },
      { step = 13, instruction = "左轉培正道", turn = "FINISH" },
    },
  },

  ["pui_ching_2"] = {
    centre = "pui_ching_road",
    name = "培正道路線二",
    steps = {
      { step = 1, instruction = "試場", turn = "STRAIGHT" },
      { step = 2, instruction = "培正道", turn = "L" },
      { step = 3, instruction = "公主道方向", turn = "MERGE" },
      { step = 4, instruction = "合流", turn = "L" },
      { step = 5, instruction = "亞皆老街", turn = "FINISH" },
    },
  },

  ["pui_ching_3"] = {
    centre = "pui_ching_road",
    name = "培正道路線三",
    steps = {
      { step = 1, instruction = "試場", turn = "STRAIGHT" },
      { step = 2, instruction = "培正道", turn = "L" },
      { step = 3, instruction = "常興街", turn = "L" },
      { step = 4, instruction = "常盛街", turn = "UTURN" },
      { step = 5, instruction = "常康街掉頭", turn = "FINISH" },
    },
  },

  ["pui_ching_4"] = {
    centre = "pui_ching_road",
    name = "培正道路線四",
    steps = {
      { step = 1, instruction = "試場", turn = "STRAIGHT" },
      { step = 2, instruction = "培正道", turn = "L" },
      { step = 3, instruction = "文福道", turn = "L" },
      { step = 4, instruction = "窩打老道", turn = "FINISH" },
    },
  },

  ["wing_hau_1"] = {
    centre = "wing_hau_street",
    name = "永孝街路線一",
    steps = {
      { step = 1, instruction = "試場開出", turn = "STRAIGHT" },
      { step = 2, instruction = "永孝街", turn = "L" },
      { step = 3, instruction = "馬頭圍道方向", turn = "L" },
      { step = 4, instruction = "漆咸道北", turn = "FINISH" },
    },
  },

  ["wing_hau_2"] = {
    centre = "wing_hau_street",
    name = "永孝街路線二",
    steps = {
      { step = 1, instruction = "試場開出", turn = "STRAIGHT" },
      { step = 2, instruction = "永孝街", turn = "L" },
      { step = 3, instruction = "土瓜灣道方向", turn = "LANE_CHANGE" },
      { step = 4, instruction = "雙線切入", turn = "FINISH" },
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

  ["ap_lei_chau_1"] = {
    centre = "ap_lei_chau",
    name = "鴨脷洲場外路線一",
    steps = {
      { step = 1, instruction = "場內乙部（泊位、掉頭）", turn = "IN_YARD" },
      { step = 2, instruction = "場外開出", turn = "STRAIGHT" },
      { step = 3, instruction = "香港仔市區", turn = "TUNNEL" },
      { step = 4, instruction = "隧道出入口", turn = "MERGE" },
      { step = 5, instruction = "快速公路匯入", turn = "FINISH" },
    },
  },

  ["ap_lei_chau_2"] = {
    centre = "ap_lei_chau",
    name = "鴨脷洲場外路線二",
    steps = {
      { step = 1, instruction = "場內乙部（泊位、掉頭）", turn = "IN_YARD" },
      { step = 2, instruction = "場外開出", turn = "STRAIGHT" },
      { step = 3, instruction = "香港仔海旁", turn = "ROUNDABOUT" },
      { step = 4, instruction = "迴旋處", turn = "FINISH" },
    },
  },

  ["yuen_long_1"] = {
    centre = "yuen_long",
    name = "元朗場外路線一",
    steps = {
      { step = 1, instruction = "場內乙部（泊位、掉頭）", turn = "IN_YARD" },
      { step = 2, instruction = "場外開出", turn = "STRAIGHT" },
      { step = 3, instruction = "元朗鄉郊道路", turn = "ROUNDABOUT" },
      { step = 4, instruction = "迴旋處", turn = "FINISH" },
    },
  },

  ["yuen_long_2"] = {
    centre = "yuen_long",
    name = "元朗場外路線二",
    steps = {
      { step = 1, instruction = "場內乙部（泊位、掉頭）", turn = "IN_YARD" },
      { step = 2, instruction = "場外開出", turn = "STRAIGHT" },
      { step = 3, instruction = "元朗鄉郊道路", turn = "STRAIGHT" },
      { step = 4, instruction = "快速路段", turn = "FINISH" },
    },
  },

  ["sha_tin_1"] = {
    centre = "sha_tin",
    name = "沙田場外路線一",
    steps = {
      { step = 1, instruction = "場內乙部（泊位、掉頭）", turn = "IN_YARD" },
      { step = 2, instruction = "場外開出", turn = "STRAIGHT" },
      { step = 3, instruction = "沙田市區", turn = "L" },
      { step = 4, instruction = "沙田圍路", turn = "FINISH" },
    },
  },

  ["sha_tin_2"] = {
    centre = "sha_tin",
    name = "沙田場外路線二",
    steps = {
      { step = 1, instruction = "場內乙部（泊位、掉頭）", turn = "IN_YARD" },
      { step = 2, instruction = "場外開出", turn = "STRAIGHT" },
      { step = 3, instruction = "沙田市區", turn = "ROUNDABOUT" },
      { step = 4, instruction = "迴旋處", turn = "FINISH" },
    },
  },

}