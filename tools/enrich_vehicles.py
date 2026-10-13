"""Enrich config/vehicles.json with detailed specs for all HK traffic vehicles.

Adds per-vehicle: year, body_type, dimensions (m), engine, power_hp,
transmission, and notes. Preserves existing fields.

Usage:
    python tools/enrich_vehicles.py
"""

from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "config", "vehicles.json")

# id -> detailed spec
DETAILS = {
    # ---------------- PRIVATE CARS (60) ----------------
    "private_toyota_corolla": {"year": 2022, "body": "Sedan", "length": 4.63, "width": 1.78, "height": 1.44, "engine": "1.8L 2ZR-FE I4", "power": 139, "trans": "CVT", "notes": "香港最常見的士以外的私家車之一"},
    "private_toyota_camry": {"year": 2022, "body": "Sedan", "length": 4.88, "width": 1.84, "height": 1.44, "engine": "2.5L A25A-FKS I4", "power": 203, "trans": "8AT", "notes": "混能版 2.5L A25A-FXS 218hp"},
    "private_toyota_prius": {"year": 2021, "body": "Hatchback", "length": 4.57, "width": 1.76, "height": 1.47, "engine": "1.8L 2ZR-FXE + MG", "power": 121, "trans": "e-CVT", "notes": "混能車，香港的士亦常用"},
    "private_toyota_yaris": {"year": 2021, "body": "Hatchback", "length": 3.94, "width": 1.69, "height": 1.51, "engine": "1.5L 1NZ-FE I4", "power": 107, "trans": "CVT/5MT", "notes": "香港考車 (類別1) 常用車"},
    "private_toyota_vios": {"year": 2020, "body": "Sedan", "length": 4.42, "width": 1.70, "height": 1.48, "engine": "1.5L 2NR-FE I4", "power": 107, "trans": "CVT", "notes": "東南亞/中國版入門轎車"},
    "private_toyota_crown": {"year": 2018, "body": "Sedan", "length": 4.91, "width": 1.80, "height": 1.46, "engine": "2.0L 8AR-FTS Turbo", "power": 245, "trans": "8AT", "notes": "香港傳統豪華房車"},
    "private_toyota_alphard": {"year": 2022, "body": "MPV", "length": 4.95, "width": 1.85, "height": 1.90, "engine": "2.5L 2AR-FE + MG", "power": 117, "trans": "e-CVT", "notes": "香港最受歡迎豪華 MPV，明星保母車"},
    "private_toyota_vellfire": {"year": 2022, "body": "MPV", "length": 4.95, "width": 1.85, "height": 1.90, "engine": "2.5L 2AR-FE + MG", "power": 117, "trans": "e-CVT", "notes": "Alphard 姊妹車型"},
    "private_toyota_sienta": {"year": 2019, "body": "MPV", "length": 4.26, "width": 1.70, "height": 1.67, "engine": "1.5L 2NR-FKE I4", "power": 109, "trans": "CVT", "notes": "香港家庭小型 MPV"},
    "private_toyota_noah": {"year": 2021, "body": "MPV", "length": 4.70, "width": 1.73, "height": 1.85, "engine": "2.0L 3ZR-FAE I4", "power": 150, "trans": "CVT", "notes": "8人座 MPV"},
    "private_toyota_rav4": {"year": 2022, "body": "SUV", "length": 4.60, "width": 1.86, "height": 1.69, "engine": "2.0L M20A-FKS I4", "power": 171, "trans": "CVT", "notes": "香港暢銷 SUV"},
    "private_toyota_harrier": {"year": 2021, "body": "SUV", "length": 4.74, "width": 1.86, "height": 1.68, "engine": "2.0L M20A-FKS I4", "power": 171, "trans": "CVT", "notes": "豪華中型 SUV"},
    "private_toyota_land_cruiser_prado": {"year": 2020, "body": "SUV", "length": 4.84, "width": 1.89, "height": 1.85, "engine": "2.8L 1GD-FTV Diesel", "power": 201, "trans": "6AT", "notes": "大型越野 SUV"},
    "private_honda_civic": {"year": 2022, "body": "Sedan/Hatch", "length": 4.68, "width": 1.80, "height": 1.41, "engine": "1.5L L15B7 Turbo", "power": 181, "trans": "CVT", "notes": "香港熱門房車"},
    "private_honda_accord": {"year": 2020, "body": "Sedan", "length": 4.90, "width": 1.86, "height": 1.45, "engine": "1.5L L15BN Turbo", "power": 192, "trans": "CVT", "notes": ""},
    "private_honda_fit": {"year": 2021, "body": "Hatchback", "length": 4.06, "width": 1.69, "height": 1.53, "engine": "1.5L L15B I4", "power": 131, "trans": "CVT", "notes": "香港暢銷小車 (Jazz)"},
    "private_honda_freed": {"year": 2020, "body": "MPV", "length": 4.31, "width": 1.70, "height": 1.74, "engine": "1.5L L15B I4", "power": 131, "trans": "CVT", "notes": "小型 7 人 MPV"},
    "private_honda_stepwgn": {"year": 2021, "body": "MPV", "length": 4.76, "width": 1.70, "height": 1.84, "engine": "1.5L L15B Turbo", "power": 148, "trans": "CVT", "notes": "7人 MPV，Waku Waku 尾門"},
    "private_honda_crv": {"year": 2021, "body": "SUV", "length": 4.63, "width": 1.86, "height": 1.68, "engine": "1.5L L15BE Turbo", "power": 193, "trans": "CVT", "notes": "香港暢銷 SUV"},
    "private_honda_hrv": {"year": 2022, "body": "SUV", "length": 4.34, "width": 1.79, "height": 1.59, "engine": "1.5L L15B I4", "power": 127, "trans": "CVT", "notes": "小型 SUV (Vezel)"},
    "private_nissan_note": {"year": 2020, "body": "Hatchback", "length": 4.10, "width": 1.70, "height": 1.52, "engine": "1.2L HR12DE e-Power", "power": 109, "trans": "e-Power", "notes": "e-Power 混能小車"},
    "private_nissan_serena": {"year": 2021, "body": "MPV", "length": 4.77, "width": 1.74, "height": 1.87, "engine": "2.0L MR20DD + e-Power", "power": 150, "trans": "CVT", "notes": "7/8人 MPV"},
    "private_nissan_xtrail": {"year": 2021, "body": "SUV", "length": 4.68, "width": 1.84, "height": 1.72, "engine": "2.0L MR20DD + e-Power", "power": 204, "trans": "e-Power", "notes": "e-Power 混能 SUV"},
    "private_nissan_qashqai": {"year": 2021, "body": "SUV", "length": 4.43, "width": 1.84, "height": 1.62, "engine": "1.3L HR13DDT Turbo", "power": 156, "trans": "CVT", "notes": "小型 SUV"},
    "private_nissan_kicks": {"year": 2022, "body": "SUV", "length": 4.30, "width": 1.76, "height": 1.59, "engine": "1.2L e-Power", "power": 127, "trans": "e-Power", "notes": "e-Power 小型 SUV"},
    "private_mazda2": {"year": 2020, "body": "Hatchback", "length": 4.06, "width": 1.69, "height": 1.50, "engine": "1.5L Skyactiv-G I4", "power": 114, "trans": "6AT", "notes": "香港小型車 (Demio)"},
    "private_mazda3": {"year": 2021, "body": "Sedan/Hatch", "length": 4.46, "width": 1.80, "height": 1.44, "engine": "2.0L Skyactiv-G I4", "power": 153, "trans": "6AT", "notes": ""},
    "private_mazda6": {"year": 2020, "body": "Sedan", "length": 4.87, "width": 1.84, "height": 1.45, "engine": "2.5L Skyactiv-G I4", "power": 192, "trans": "6AT", "notes": ""},
    "private_mazda_cx3": {"year": 2020, "body": "SUV", "length": 4.28, "width": 1.77, "height": 1.54, "engine": "2.0L Skyactiv-G I4", "power": 150, "trans": "6AT", "notes": ""},
    "private_mazda_cx5": {"year": 2021, "body": "SUV", "length": 4.58, "width": 1.85, "height": 1.68, "engine": "2.5L Skyactiv-G I4", "power": 194, "trans": "6AT", "notes": ""},
    "private_mitsubishi_lancer": {"year": 2016, "body": "Sedan", "length": 4.57, "width": 1.76, "height": 1.49, "engine": "1.8L 4B10 I4", "power": 141, "trans": "CVT", "notes": "香港的士曾用 Lancer 車型"},
    "private_mitsubishi_outlander": {"year": 2020, "body": "SUV", "length": 4.71, "width": 1.81, "height": 1.71, "engine": "2.4L 4J12 I4 + PHEV", "power": 135, "trans": "CVT", "notes": "PHEV 版 94km 純電續航"},
    "private_suzuki_swift": {"year": 2021, "body": "Hatchback", "length": 3.85, "width": 1.74, "height": 1.50, "engine": "1.2L K12D I4", "power": 90, "trans": "CVT/5MT", "notes": "輕巧小車"},
    "private_suzuki_ignis": {"year": 2020, "body": "Hatchback", "length": 3.70, "width": 1.66, "height": 1.60, "engine": "1.2L K12C I4", "power": 90, "trans": "CVT/5MT", "notes": "迷你 SUV 風格"},
    "private_subaru_impreza": {"year": 2020, "body": "Sedan/Hatch", "length": 4.46, "width": 1.78, "height": 1.50, "engine": "2.0L FB20 + e-Boxer", "power": 152, "trans": "CVT", "notes": "水平對向引擎"},
    "private_subaru_forester": {"year": 2021, "body": "SUV", "length": 4.64, "width": 1.81, "height": 1.73, "engine": "2.0L FB20 + e-Boxer", "power": 152, "trans": "CVT", "notes": "四驅 SUV"},
    "private_volkswagen_golf": {"year": 2021, "body": "Hatchback", "length": 4.28, "width": 1.79, "height": 1.48, "engine": "1.4L EA211 TSI Turbo", "power": 148, "trans": "7DSG", "notes": ""},
    "private_volkswagen_passat": {"year": 2020, "body": "Sedan", "length": 4.93, "width": 1.84, "height": 1.47, "engine": "2.0L EA888 TSI", "power": 190, "trans": "7DSG", "notes": ""},
    "private_volkswagen_tiguan": {"year": 2021, "body": "SUV", "length": 4.51, "width": 1.84, "height": 1.66, "engine": "2.0L EA888 TSI", "power": 190, "trans": "7DSG", "notes": ""},
    "private_skoda_octavia": {"year": 2021, "body": "Sedan/Hatch", "length": 4.69, "width": 1.83, "height": 1.47, "engine": "1.5L EA211 TSI", "power": 148, "trans": "7DSG", "notes": ""},
    "private_mercedes_c_class": {"year": 2021, "body": "Sedan", "length": 4.75, "width": 1.82, "height": 1.44, "engine": "1.5L M264 + EQ Boost", "power": 184, "trans": "9AT", "notes": ""},
    "private_mercedes_e_class": {"year": 2020, "body": "Sedan", "length": 4.94, "width": 1.86, "height": 1.47, "engine": "2.0L M264 Turbo", "power": 258, "trans": "9AT", "notes": ""},
    "private_mercedes_glc": {"year": 2021, "body": "SUV", "length": 4.66, "width": 1.90, "height": 1.64, "engine": "2.0L M264 Turbo", "power": 258, "trans": "9AT", "notes": ""},
    "private_bmw_3_series": {"year": 2021, "body": "Sedan", "length": 4.71, "width": 1.83, "height": 1.44, "engine": "2.0L B48 Turbo", "power": 184, "trans": "8AT", "notes": ""},
    "private_bmw_5_series": {"year": 2020, "body": "Sedan", "length": 4.96, "width": 1.87, "height": 1.48, "engine": "2.0L B48 Turbo", "power": 252, "trans": "8AT", "notes": ""},
    "private_bmw_x3": {"year": 2021, "body": "SUV", "length": 4.71, "width": 1.89, "height": 1.68, "engine": "2.0L B48 Turbo", "power": 184, "trans": "8AT", "notes": ""},
    "private_audi_a3": {"year": 2021, "body": "Sedan/Hatch", "length": 4.34, "width": 1.82, "height": 1.43, "engine": "1.4L EA211 TFSI", "power": 148, "trans": "7DSG", "notes": ""},
    "private_audi_a4": {"year": 2020, "body": "Sedan", "length": 4.76, "width": 1.84, "height": 1.43, "engine": "2.0L EA888 TFSI", "power": 190, "trans": "7DSG", "notes": ""},
    "private_audi_q5": {"year": 2021, "body": "SUV", "length": 4.68, "width": 1.89, "height": 1.66, "engine": "2.0L EA888 TFSI", "power": 252, "trans": "7DSG", "notes": ""},
    "private_lexus_is": {"year": 2020, "body": "Sedan", "length": 4.71, "width": 1.82, "height": 1.44, "engine": "2.0L 8AR-FTS Turbo", "power": 245, "trans": "8AT", "notes": "IS200t/IS300"},
    "private_lexus_es": {"year": 2021, "body": "Sedan", "length": 4.98, "width": 1.87, "height": 1.45, "engine": "2.5L A25A-FXS + MG", "power": 218, "trans": "e-CVT", "notes": "混能豪華房車"},
    "private_lexus_rx": {"year": 2021, "body": "SUV", "length": 4.89, "width": 1.90, "height": 1.71, "engine": "3.5L 2GR-FXS V6 + MG", "power": 313, "trans": "e-CVT", "notes": "RX450h 混能"},
    "private_tesla_model3": {"year": 2023, "body": "Sedan", "length": 4.72, "width": 1.85, "height": 1.44, "engine": "EV 雙摩打", "power": 283, "trans": "1AT", "notes": "香港暢銷電動車"},
    "private_tesla_modely": {"year": 2023, "body": "SUV", "length": 4.75, "width": 1.92, "height": 1.62, "engine": "EV 雙摩打", "power": 378, "trans": "1AT", "notes": ""},
    "private_hyundai_kona": {"year": 2021, "body": "SUV", "length": 4.21, "width": 1.80, "height": 1.57, "engine": "1.6L G4FJ Turbo / EV", "power": 195, "trans": "7DCT", "notes": "Kona EV 64kWh"},
    "private_kia_niro": {"year": 2021, "body": "SUV", "length": 4.42, "width": 1.83, "height": 1.55, "engine": "1.6L G4LE + MG", "power": 139, "trans": "6DCT", "notes": "混能 SUV"},
    "private_kia_sportage": {"year": 2022, "body": "SUV", "length": 4.66, "width": 1.87, "height": 1.64, "engine": "2.0L R Diesel / 1.6T", "power": 185, "trans": "8AT", "notes": ""},
    "private_mini_cooper": {"year": 2021, "body": "Hatchback", "length": 3.86, "width": 1.73, "height": 1.42, "engine": "1.5L B38 Turbo", "power": 134, "trans": "7DCT", "notes": ""},
    "private_range_rover_evoque": {"year": 2021, "body": "SUV", "length": 4.37, "width": 1.90, "height": 1.65, "engine": "2.0L AJ200 Turbo", "power": 249, "trans": "9AT", "notes": ""},
    "private_volvo_xc40": {"year": 2021, "body": "SUV", "length": 4.44, "width": 1.87, "height": 1.65, "engine": "2.0L B4 + MG / EV", "power": 197, "trans": "8AT", "notes": "XC40 Recharge EV 402hp"},

    # ---------------- COMMERCIAL (25) ----------------
    "commercial_toyota_crown_comfort_taxi": {"year": 2015, "body": "Taxi Sedan", "length": 4.60, "width": 1.70, "height": 1.52, "engine": "2.0L 1TR-FE LPG", "power": 114, "trans": "4AT", "notes": "香港經典的士，LPG 石油氣引擎"},
    "commercial_toyota_comfort_taxi": {"year": 2015, "body": "Taxi Sedan", "length": 4.60, "width": 1.70, "height": 1.52, "engine": "2.0L 1TR-FE LPG", "power": 114, "trans": "4AT", "notes": "Comfort 的士，Crown Comfort 姊妹"},
    "commercial_toyota_jpn_taxi": {"year": 2019, "body": "Taxi MPV", "length": 4.40, "width": 1.70, "height": 1.75, "engine": "1.5L 2NR-FKE Hybrid", "power": 101, "trans": "e-CVT", "notes": "新一代混能的士，輪椅友善"},
    "commercial_nissan_cedric_taxi": {"year": 2010, "body": "Taxi Sedan", "length": 4.59, "width": 1.70, "height": 1.44, "engine": "2.0L NA20P LPG", "power": 100, "trans": "4AT", "notes": "舊款日產的士"},
    "commercial_toyota_hiace": {"year": 2021, "body": "Van", "length": 4.70, "width": 1.70, "height": 1.98, "engine": "2.8L 1GD-FTV Diesel", "power": 177, "trans": "6AT", "notes": "香港最常見客貨車"},
    "commercial_nissan_nv200": {"year": 2020, "body": "Van", "length": 4.40, "width": 1.70, "height": 1.86, "engine": "1.6L HR16DE I4", "power": 108, "trans": "CVT", "notes": "小型客貨車"},
    "commercial_ford_transit": {"year": 2020, "body": "Van", "length": 5.53, "width": 2.06, "height": 2.41, "engine": "2.0L EcoBlue Diesel", "power": 168, "trans": "6MT/8AT", "notes": ""},
    "commercial_mercedes_vito": {"year": 2021, "body": "Van", "length": 5.14, "width": 1.93, "height": 1.90, "engine": "2.0L OM654 Diesel", "power": 161, "trans": "9AT", "notes": ""},
    "commercial_volkswagen_transporter": {"year": 2020, "body": "Van", "length": 4.90, "width": 1.90, "height": 1.99, "engine": "2.0L TDI Diesel", "power": 147, "trans": "7DSG", "notes": ""},
    "commercial_toyota_proace": {"year": 2021, "body": "Van", "length": 4.96, "width": 1.92, "height": 1.91, "engine": "2.0L Diesel", "power": 143, "trans": "8AT", "notes": ""},
    "commercial_mitsubishi_canter": {"year": 2020, "body": "Light Truck", "length": 4.99, "width": 1.70, "height": 2.00, "engine": "3.0L 4P10 Diesel", "power": 150, "trans": "6MT/6AT", "notes": "香港常見輕型貨車"},
    "commercial_isuzu_elf": {"year": 2020, "body": "Light Truck", "length": 4.97, "width": 1.70, "height": 2.00, "engine": "3.0L 4JJ1 Diesel", "power": 150, "trans": "6MT/6AT", "notes": "NPR 系列"},
    "commercial_hino_dutro": {"year": 2020, "body": "Light Truck", "length": 4.99, "width": 1.70, "height": 2.01, "engine": "4.0L N04C Diesel", "power": 150, "trans": "6MT/6AT", "notes": ""},
    "commercial_toyota_dyna": {"year": 2020, "body": "Light Truck", "length": 4.99, "width": 1.70, "height": 2.01, "engine": "4.0L N04C Diesel", "power": 150, "trans": "6MT", "notes": ""},
    "commercial_isuzu_forward": {"year": 2021, "body": "Medium Truck", "length": 6.95, "width": 2.30, "height": 2.60, "engine": "6.0L 6HK1 Diesel", "power": 240, "trans": "6MT/6AT", "notes": "中型貨車"},
    "commercial_hino_300": {"year": 2021, "body": "Medium Truck", "length": 6.40, "width": 2.20, "height": 2.55, "engine": "5.1L N04C Diesel", "power": 180, "trans": "6MT", "notes": ""},
    "commercial_refrigerated_van": {"year": 2020, "body": "Refrigerated Van", "length": 5.50, "width": 2.00, "height": 2.50, "engine": "Diesel 3.0L", "power": 150, "trans": "6MT", "notes": "凍櫃車"},
    "commercial_box_truck": {"year": 2020, "body": "Box Truck", "length": 7.00, "width": 2.30, "height": 2.80, "engine": "Diesel 5.0L", "power": 220, "trans": "6MT", "notes": ""},
    "commercial_lpg_delivery_truck": {"year": 2018, "body": "Box Truck", "length": 6.50, "width": 2.20, "height": 2.70, "engine": "Diesel 4.0L", "power": 180, "trans": "6MT", "notes": "石油氣運送車"},
    "commercial_cement_mixer": {"year": 2020, "body": "Mixer Truck", "length": 8.20, "width": 2.50, "height": 3.50, "engine": "Diesel 12.0L", "power": 380, "trans": "9MT", "notes": "混凝土攪拌車"},
    "commercial_tow_truck": {"year": 2019, "body": "Tow Truck", "length": 5.80, "width": 2.20, "height": 2.50, "engine": "Diesel 5.0L", "power": 220, "trans": "6MT", "notes": "拖車"},
    "commercial_courier_van": {"year": 2021, "body": "Van", "length": 4.40, "width": 1.70, "height": 1.90, "engine": "1.5L I4", "power": 108, "trans": "CVT", "notes": "快遞貨 Van"},
    "commercial_food_delivery_van": {"year": 2021, "body": "Van", "length": 4.40, "width": 1.70, "height": 1.90, "engine": "1.5L I4", "power": 108, "trans": "CVT", "notes": "食物速遞車"},
    "commercial_construction_pickup": {"year": 2019, "body": "Pickup", "length": 5.30, "width": 1.85, "height": 1.80, "engine": "Diesel 2.5L", "power": 160, "trans": "6MT", "notes": "地盤工程車"},
    "commercial_waste_collection_truck": {"year": 2020, "body": "Waste Truck", "length": 7.50, "width": 2.50, "height": 3.20, "engine": "Diesel 10.0L", "power": 340, "trans": "9MT", "notes": "垃圾收集車"},

    # ---------------- PUBLIC/SPECIAL (15) ----------------
    "public_police_patrol_sedan": {"year": 2020, "body": "Patrol Sedan", "length": 4.90, "width": 1.85, "height": 1.46, "engine": "2.0L Turbo I4", "power": 190, "trans": "8AT", "notes": "香港警車 (BMW 5系/平治E系)"},
    "public_police_patrol_suv": {"year": 2021, "body": "Patrol SUV", "length": 4.70, "width": 1.90, "height": 1.70, "engine": "2.0L Turbo I4", "power": 250, "trans": "8AT", "notes": "警隊 SUV (寶馬 X5/平治 GLC)"},
    "public_ambulance_van": {"year": 2020, "body": "Ambulance", "length": 5.60, "width": 2.10, "height": 2.60, "engine": "Diesel 3.0L", "power": 180, "trans": "6AT", "notes": "消防處救護車 (平治 Sprinter)"},
    "public_fire_engine": {"year": 2021, "body": "Fire Engine", "length": 9.50, "width": 2.50, "height": 3.30, "engine": "Diesel 12.0L", "power": 420, "trans": "9MT", "notes": "消防車 (Scania/富豪)"},
    "public_fire_command_suv": {"year": 2020, "body": "Command SUV", "length": 4.70, "width": 1.90, "height": 1.80, "engine": "Diesel 2.0L", "power": 200, "trans": "8AT", "notes": "消防指揮車"},
    "public_government_utility_van": {"year": 2019, "body": "Utility Van", "length": 4.70, "width": 1.70, "height": 1.98, "engine": "Diesel 2.8L", "power": 177, "trans": "6AT", "notes": "政府部門客貨車"},
    "public_road_maintenance_truck": {"year": 2020, "body": "Maintenance Truck", "length": 7.00, "width": 2.30, "height": 2.80, "engine": "Diesel 6.0L", "power": 250, "trans": "6MT", "notes": "路政署維修車"},
    "public_traffic_enforcement_sedan": {"year": 2020, "body": "Patrol Sedan", "length": 4.80, "width": 1.85, "height": 1.45, "engine": "2.0L I4", "power": 190, "trans": "8AT", "notes": "交通執法車"},
    "public_driving_school_sedan": {"year": 2020, "body": "Learner Sedan", "length": 4.40, "width": 1.70, "height": 1.45, "engine": "1.5L I4", "power": 107, "trans": "5MT", "notes": "學車 (教車師傅車)"},
    "public_driving_school_hatchback": {"year": 2020, "body": "Learner Hatchback", "length": 3.95, "width": 1.69, "height": 1.51, "engine": "1.5L I4", "power": 107, "trans": "5MT", "notes": "學車 (Yaris/Fit)"},
    "public_security_patrol_van": {"year": 2019, "body": "Security Van", "length": 4.70, "width": 1.70, "height": 1.98, "engine": "Diesel 2.8L", "power": 177, "trans": "6AT", "notes": "保安巡邏車"},
    "public_prison_transport_van": {"year": 2018, "body": "Prison Van", "length": 6.50, "width": 2.20, "height": 2.60, "engine": "Diesel 5.0L", "power": 220, "trans": "6MT", "notes": "懲教署囚車"},
    "public_customs_patrol_suv": {"year": 2021, "body": "Patrol SUV", "length": 4.80, "width": 1.90, "height": 1.75, "engine": "2.0L Turbo", "power": 250, "trans": "8AT", "notes": "海關巡邏車"},
    "public_emergency_recovery_vehicle": {"year": 2019, "body": "Recovery Vehicle", "length": 5.80, "width": 2.20, "height": 2.50, "engine": "Diesel 5.0L", "power": 220, "trans": "6MT", "notes": "緊急救援拖車"},
    "public_mobile_command_vehicle": {"year": 2020, "body": "Command Bus", "length": 8.00, "width": 2.40, "height": 3.00, "engine": "Diesel 7.0L", "power": 300, "trans": "6MT", "notes": "流動指揮車"},
}


def main() -> None:
    with open(PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = 0
    for v in data["vehicles"]:
        details = DETAILS.get(v["id"])
        if details:
            v["year"] = details["year"]
            v["body_type"] = details["body"]
            v["dimensions_m"] = {
                "length": details["length"],
                "width": details["width"],
                "height": details["height"],
            }
            v["engine"] = details["engine"]
            v["power_hp"] = details["power"]
            v["transmission"] = details["trans"]
            if details.get("notes"):
                v["notes"] = details["notes"]
            enriched += 1

    data["catalog_size"] = len(data["vehicles"])
    data["enriched_at"] = "2026-10-13"
    data["enrichment_note"] = "Detailed specs (year, body, dimensions, engine, power) added for all vehicles."

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Enriched {enriched}/{len(data['vehicles'])} vehicles in {PATH}")


if __name__ == "__main__":
    main()
