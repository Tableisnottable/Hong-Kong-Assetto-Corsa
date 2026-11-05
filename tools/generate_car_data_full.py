"""Generate complete Assetto Corsa car data files from real vehicle specs.

Reads specs from car/driving test car/ and generates a full AC data/ folder
matching the structure of working mod cars (hk51_traffic_*).

Usage:
    python tools/generate_car_data_full.py

Generates per car:
    data/car.ini, engine.ini, power.lut, drivetrain.ini, suspensions.ini,
    tyres.ini, brakes.ini, cameras.ini, lights.ini, lods.ini, setup.ini,
    electronics.ini, ai.ini, colliders.ini, driver3d.ini, mirrors.ini,
    sounds.ini, aero.ini, damage.ini, fuel_cons.ini, ambient_shadows.ini,
    analog_instruments.ini, digital_instruments.ini, dash_cam.ini,
    suspension_graphics.ini, escmode.ini, blurred_objects.ini,
    street_front.lut, street_rear.lut, street90_front.lut, street90_rear.lut,
    tcurve_street.lut, tcurve_street90.lut, throttle.lut, power.lut
"""

from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARS_DIR = os.path.join(ROOT, "content", "cars")

# Vehicle specs (from car/driving test car/ spec sheets)
VEHICLES = {
    "hk_cat1_toyota_yaris": {
        "name": "Toyota Yaris (Manual)",
        "short": "Yaris 5MT",
        "mass": 1100, "wheelbase": 2.510, "track_f": 1.485, "track_r": 1.470,
        "length": 3.950, "width": 1.695, "height": 1.510, "fuel": 42,
        "steer_lock": 450, "steer_ratio": -14.8, "drivetrain": "FWD",
        "power_hp": 107, "torque_nm": 140, "rpm_power": 6000,
        "rpm_torque": 4200, "rpm_idle": 700, "rpm_limit": 6400,
        "gears": [3.545, 1.904, 1.310, 0.969, 0.815], "final": 3.722,
        "reverse": 3.250, "auto": False, "fuel_type": "petrol",
        "tyre_w": 175, "tyre_a": 65, "rim": 15,
        "brake_f": 255, "brake_r": 200, "rear_drum": True,
        "front_susp": "MacPherson", "rear_susp": "TorsionBeam",
        "inertia": "1.4,1.2,3.5", "cg_height": 0.55,
        "drivetrain_type": "FWD", "cg_front_pct": 0.62,
        "front_spring": 30000, "rear_spring": 28000,
        "front_damper_bump": 2500, "front_damper_rebound": 3500,
        "rear_damper_bump": 2500, "rear_damper_rebound": 3500,
        "camber_f": -0.5, "camber_r": -0.5, "toe_f": 0.05, "toe_r": 0.05,
        "antiroll_f": 20000, "antiroll_r": 18000,
        "tyre_grip_dry": 1.0, "tyre_grip_wet": 0.85,
        "tyre_load": 4000, "tyre_radius": 0.317,
        "brake_torque": 2500, "brake_bias": 0.65,
        "aero_drag": 0.30, "aero_front": 0.15, "aero_rear": 0.10,
        "fuel_consumption": 0.0035,
        "engine_inertia": 0.12, "coast_torque": 120,
        "ffmult": 1.0, "steer_assist": 1.0,
        "driver_eyes": "0.0,1.1,-0.15",
        "bumper_cam": "0.0,0.5,1.7", "bonnet_cam": "0.0,0.5,0.4",
        "mirror_pos": "0.0,1.0,-1.8",
        "pickup_front": -0.31, "pickup_rear": -0.31,
        "graphics_offset": "0,-0.495,-0.4",
        "graphics_pitch": -0.2,
        "instruments": "analog",
    },
    "hk_cat1a_toyota_prius": {
        "name": "Toyota Prius (Hybrid)",
        "short": "Prius e-CVT",
        "mass": 1435, "wheelbase": 2.700, "track_f": 1.535, "track_r": 1.540,
        "length": 4.540, "width": 1.760, "height": 1.470, "fuel": 43,
        "steer_lock": 360, "steer_ratio": -13.4, "drivetrain": "FWD",
        "power_hp": 121, "torque_nm": 163, "rpm_power": 5200,
        "rpm_torque": 3600, "rpm_idle": 1000, "rpm_limit": 5500,
        "gears": [2.800, 1.800, 1.200, 0.900, 0.700], "final": 3.200,
        "reverse": 2.800, "auto": True, "fuel_type": "petrol",
        "tyre_w": 195, "tyre_a": 65, "rim": 15,
        "brake_f": 255, "brake_r": 259, "rear_drum": False,
        "front_susp": "MacPherson", "rear_susp": "DoubleWishbone",
        "inertia": "1.6,1.4,4.0", "cg_height": 0.54,
        "drivetrain_type": "FWD", "cg_front_pct": 0.6,
        "front_spring": 32000, "rear_spring": 30000,
        "front_damper_bump": 2800, "front_damper_rebound": 3800,
        "rear_damper_bump": 2800, "rear_damper_rebound": 3800,
        "camber_f": -0.5, "camber_r": -0.5, "toe_f": 0.05, "toe_r": 0.05,
        "antiroll_f": 22000, "antiroll_r": 20000,
        "tyre_grip_dry": 1.0, "tyre_grip_wet": 0.85,
        "tyre_load": 4500, "tyre_radius": 0.317,
        "brake_torque": 2800, "brake_bias": 0.62,
        "aero_drag": 0.24, "aero_front": 0.14, "aero_rear": 0.10,
        "fuel_consumption": 0.0030,
        "engine_inertia": 0.10, "coast_torque": 100,
        "ffmult": 1.0, "steer_assist": 1.0,
        "driver_eyes": "0.0,1.1,-0.15",
        "bumper_cam": "0.0,0.5,1.7", "bonnet_cam": "0.0,0.5,0.4",
        "mirror_pos": "0.0,1.0,-2.0",
        "pickup_front": -0.31, "pickup_rear": -0.31,
        "graphics_offset": "0,-0.495,-0.4",
        "graphics_pitch": -0.2,
        "instruments": "digital",
    },
    "hk_cat2_toyota_hiace_mt": {
        "name": "Toyota HiAce (Manual)",
        "short": "HiAce 5MT",
        "mass": 2600, "wheelbase": 2.570, "track_f": 1.500, "track_r": 1.480,
        "length": 4.695, "width": 1.695, "height": 1.980, "fuel": 70,
        "steer_lock": 420, "steer_ratio": -16.0, "drivetrain": "RWD",
        "power_hp": 177, "torque_nm": 420, "rpm_power": 3400,
        "rpm_torque": 1600, "rpm_idle": 750, "rpm_limit": 4200,
        "gears": [4.313, 2.330, 1.436, 1.000, 0.788], "final": 3.909,
        "reverse": 4.220, "auto": False, "fuel_type": "diesel",
        "tyre_w": 195, "tyre_a": 80, "rim": 15,
        "brake_f": 285, "brake_r": 254, "rear_drum": True,
        "front_susp": "DoubleWishbone", "rear_susp": "LeafSpring",
        "inertia": "2.0,1.8,5.0", "cg_height": 0.70,
        "drivetrain_type": "RWD", "cg_front_pct": 0.55,
        "front_spring": 45000, "rear_spring": 55000,
        "front_damper_bump": 3500, "front_damper_rebound": 4500,
        "rear_damper_bump": 3500, "rear_damper_rebound": 4500,
        "camber_f": -0.5, "camber_r": -0.5, "toe_f": 0.05, "toe_r": 0.05,
        "antiroll_f": 30000, "antiroll_r": 25000,
        "tyre_grip_dry": 1.0, "tyre_grip_wet": 0.85,
        "tyre_load": 5500, "tyre_radius": 0.330,
        "brake_torque": 3500, "brake_bias": 0.60,
        "aero_drag": 0.45, "aero_front": 0.20, "aero_rear": 0.15,
        "fuel_consumption": 0.0050,
        "engine_inertia": 0.20, "coast_torque": 180,
        "ffmult": 1.2, "steer_assist": 1.0,
        "driver_eyes": "0.0,1.3,-0.15",
        "bumper_cam": "0.0,0.6,1.7", "bonnet_cam": "0.0,0.6,0.4",
        "mirror_pos": "0.0,1.3,-2.0",
        "pickup_front": -0.35, "pickup_rear": -0.35,
        "graphics_offset": "0,-0.495,-0.4",
        "graphics_pitch": -0.2,
        "instruments": "analog",
    },
    "hk_cat2a_toyota_hiace_at": {
        "name": "Toyota HiAce (Auto Ballast)",
        "short": "HiAce 6AT",
        "mass": 2600, "wheelbase": 2.570, "track_f": 1.500, "track_r": 1.480,
        "length": 4.695, "width": 1.695, "height": 1.980, "fuel": 70,
        "steer_lock": 420, "steer_ratio": -16.0, "drivetrain": "RWD",
        "power_hp": 177, "torque_nm": 450, "rpm_power": 3400,
        "rpm_torque": 1800, "rpm_idle": 750, "rpm_limit": 4200,
        "gears": [3.600, 2.090, 1.488, 1.000, 0.687, 0.580], "final": 3.909,
        "reverse": 3.732, "auto": True, "fuel_type": "diesel",
        "tyre_w": 195, "tyre_a": 80, "rim": 15,
        "brake_f": 285, "brake_r": 254, "rear_drum": True,
        "front_susp": "DoubleWishbone", "rear_susp": "LeafSpring",
        "inertia": "2.0,1.8,5.0", "cg_height": 0.70,
        "drivetrain_type": "RWD", "cg_front_pct": 0.55,
        "front_spring": 45000, "rear_spring": 55000,
        "front_damper_bump": 3500, "front_damper_rebound": 4500,
        "rear_damper_bump": 3500, "rear_damper_rebound": 4500,
        "camber_f": -0.5, "camber_r": -0.5, "toe_f": 0.05, "toe_r": 0.05,
        "antiroll_f": 30000, "antiroll_r": 25000,
        "tyre_grip_dry": 1.0, "tyre_grip_wet": 0.85,
        "tyre_load": 5500, "tyre_radius": 0.330,
        "brake_torque": 3500, "brake_bias": 0.60,
        "aero_drag": 0.45, "aero_front": 0.20, "aero_rear": 0.15,
        "fuel_consumption": 0.0050,
        "engine_inertia": 0.20, "coast_torque": 180,
        "ffmult": 1.2, "steer_assist": 1.0,
        "driver_eyes": "0.0,1.3,-0.15",
        "bumper_cam": "0.0,0.6,1.7", "bonnet_cam": "0.0,0.6,0.4",
        "mirror_pos": "0.0,1.3,-2.0",
        "pickup_front": -0.35, "pickup_rear": -0.35,
        "graphics_offset": "0,-0.495,-0.4",
        "graphics_pitch": -0.2,
        "instruments": "analog",
    },
    "hk_cat17_adl_e500_gen1": {
        "name": "ADL Enviro500 Gen 1",
        "short": "E500 Gen1",
        "mass": 14200, "wheelbase": 5.950, "track_f": 2.050, "track_r": 1.850,
        "length": 12.000, "width": 2.550, "height": 4.300, "fuel": 300,
        "steer_lock": 320, "steer_ratio": -20.0, "drivetrain": "RWD",
        "power_hp": 340, "torque_nm": 1500, "rpm_power": 2100,
        "rpm_torque": 1300, "rpm_idle": 600, "rpm_limit": 2500,
        "gears": [3.360, 1.910, 1.420, 1.000, 0.720, 0.610], "final": 4.100,
        "reverse": 3.500, "auto": True, "fuel_type": "diesel",
        "tyre_w": 295, "tyre_a": 80, "rim": 22,
        "brake_f": 430, "brake_r": 430, "rear_drum": False,
        "front_susp": "AirSuspension", "rear_susp": "AirSuspension",
        "inertia": "8.0,7.0,20.0", "cg_height": 1.20,
        "drivetrain_type": "RWD", "cg_front_pct": 0.5,
        "front_spring": 120000, "rear_spring": 140000,
        "front_damper_bump": 8000, "front_damper_rebound": 10000,
        "rear_damper_bump": 8000, "rear_damper_rebound": 10000,
        "camber_f": -0.3, "camber_r": -0.3, "toe_f": 0.05, "toe_r": 0.05,
        "antiroll_f": 80000, "antiroll_r": 70000,
        "tyre_grip_dry": 1.0, "tyre_grip_wet": 0.85,
        "tyre_load": 15000, "tyre_radius": 0.510,
        "brake_torque": 15000, "brake_bias": 0.55,
        "aero_drag": 0.80, "aero_front": 0.40, "aero_rear": 0.30,
        "fuel_consumption": 0.0150,
        "engine_inertia": 1.50, "coast_torque": 800,
        "ffmult": 2.0, "steer_assist": 1.0,
        "driver_eyes": "0.0,2.5,-0.15",
        "bumper_cam": "0.0,1.0,5.5", "bonnet_cam": "0.0,1.0,0.5",
        "mirror_pos": "0.0,2.5,-5.5",
        "pickup_front": -0.50, "pickup_rear": -0.50,
        "graphics_offset": "0,-0.495,-0.4",
        "graphics_pitch": -0.2,
        "instruments": "analog",
    },
    "hk_cat17a_adl_e500_mmc": {
        "name": "ADL Enviro500 MMC Gen 2",
        "short": "E500 MMC",
        "mass": 15100, "wheelbase": 5.980, "track_f": 2.050, "track_r": 1.850,
        "length": 12.000, "width": 2.550, "height": 4.347, "fuel": 300,
        "steer_lock": 320, "steer_ratio": -20.0, "drivetrain": "RWD",
        "power_hp": 340, "torque_nm": 1500, "rpm_power": 2100,
        "rpm_torque": 1200, "rpm_idle": 600, "rpm_limit": 2500,
        "gears": [3.360, 1.910, 1.420, 1.000, 0.720, 0.610], "final": 4.100,
        "reverse": 3.500, "auto": True, "fuel_type": "diesel",
        "tyre_w": 295, "tyre_a": 80, "rim": 22,
        "brake_f": 430, "brake_r": 430, "rear_drum": False,
        "front_susp": "AirSuspension", "rear_susp": "AirSuspension",
        "inertia": "8.5,7.5,21.0", "cg_height": 1.20,
        "drivetrain_type": "RWD", "cg_front_pct": 0.5,
        "front_spring": 130000, "rear_spring": 150000,
        "front_damper_bump": 8500, "front_damper_rebound": 10500,
        "rear_damper_bump": 8500, "rear_damper_rebound": 10500,
        "camber_f": -0.3, "camber_r": -0.3, "toe_f": 0.05, "toe_r": 0.05,
        "antiroll_f": 85000, "antiroll_r": 75000,
        "tyre_grip_dry": 1.0, "tyre_grip_wet": 0.85,
        "tyre_load": 15000, "tyre_radius": 0.510,
        "brake_torque": 15000, "brake_bias": 0.55,
        "aero_drag": 0.80, "aero_front": 0.40, "aero_rear": 0.30,
        "fuel_consumption": 0.0150,
        "engine_inertia": 1.50, "coast_torque": 800,
        "ffmult": 2.0, "steer_assist": 1.0,
        "driver_eyes": "0.0,2.5,-0.15",
        "bumper_cam": "0.0,1.0,5.5", "bonnet_cam": "0.0,1.0,0.5",
        "mirror_pos": "0.0,2.5,-5.5",
        "pickup_front": -0.50, "pickup_rear": -0.50,
        "graphics_offset": "0,-0.495,-0.4",
        "graphics_pitch": -0.2,
        "instruments": "analog",
    },
}


def write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def power_lut(v: dict) -> str:
    """Generate power.lut (rpm|torque) from specs."""
    lines = []
    idle = v["rpm_idle"]
    limit = v["rpm_limit"]
    peak_t = v["rpm_torque"]
    peak_p = v["rpm_power"]
    tq = v["torque_nm"]
    steps = 12
    for i in range(steps + 1):
        rpm = int(idle + (limit - idle) * i / steps)
        if rpm <= peak_t:
            f = 0.55 + 0.45 * (rpm - idle) / max(1, (peak_t - idle))
        elif rpm <= peak_p:
            f = 1.0
        else:
            f = max(0.55, 1.0 - 0.45 * (rpm - peak_p) / max(1, (limit - peak_p)))
        lines.append(f"{rpm}|{int(tq * f)}")
    return "\n".join(lines)


def tcurve_lut(v: dict) -> str:
    """Generate tcurve (tyre curve) lut."""
    grip = v["tyre_grip_dry"]
    return f"0|{grip:.3f}\n1|{grip:.3f}\n2|{grip:.3f}\n3|{grip:.3f}\n4|{grip:.3f}\n5|{grip:.3f}"


def street_lut(v: dict) -> str:
    """Generate street tyre grip lut."""
    return f"0|{v['tyre_grip_dry']:.3f}\n1|{v['tyre_grip_dry']:.3f}\n2|{v['tyre_grip_dry']:.3f}\n3|{v['tyre_grip_dry']:.3f}\n4|{v['tyre_grip_dry']:.3f}\n5|{v['tyre_grip_dry']:.3f}"


def throttle_lut(v: dict) -> str:
    return "0|0\n1|1\n2|1\n3|1\n4|1\n5|1"


def generate_car(car_id: str, v: dict) -> None:
    data_dir = os.path.join(CARS_DIR, car_id, "data")
    os.makedirs(data_dir, exist_ok=True)

    # car.ini
    write(os.path.join(data_dir, "car.ini"), f"""; Generated by tools/generate_car_data_full.py
[HEADER]
VERSION=1

[INFO]
SCREEN_NAME={v['name']}
SHORT_NAME={v['short']}

[BASIC]
GRAPHICS_OFFSET={v['graphics_offset']}
GRAPHICS_PITCH_ROTATION={v['graphics_pitch']}
TOTALMASS={v['mass']}
INERTIA={v['inertia']}

[GRAPHICS]
DRIVEREYES={v['driver_eyes']}
ONBOARD_EXPOSURE=17
OUTBOARD_EXPOSURE=31
ON_BOARD_PITCH_ANGLE=-4.286740
BUMPER_CAMERA_POS={v['bumper_cam']}
BONNET_CAMERA_POS={v['bonnet_cam']}
MIRROR_POSITION={v['mirror_pos']}
USE_ANIMATED_SUSPENSIONS=0
VIRTUAL_MIRROR_ENABLED=0
SHAKE_MUL=3
FUEL_LIGHT_MIN_LITERS=7
BONNET_CAMERA_PITCH=-0.572948
BUMPER_CAMERA_PITCH=-0.572958

[CONTROLS]
FFMULT={v['ffmult']}
STEER_ASSIST={v['steer_assist']}
STEER_LOCK={v['steer_lock']}
STEER_RATIO={v['steer_ratio']}
LINEAR_STEER_ROD_RATIO=0.0021

[FUEL]
CONSUMPTION={v['fuel_consumption']}
FUEL={v['fuel']}
MAX_FUEL={v['fuel']}

[FUELTANK]
POSITION=0,0.2,-2.2

[RIDE]
PICKUP_FRONT_HEIGHT={v['pickup_front']}
PICKUP_REAR_HEIGHT={v['pickup_rear']}

[PIT_STOP]
TYRE_CHANGE_TIME_SEC=10
FUEL_LITER_TIME_SEC=0.6
BODY_REPAIR_TIME_SEC=20
ENGINE_REPAIR_TIME_SEC=2
SUSP_REPAIR_TIME_SEC=30
""")

    # engine.ini
    write(os.path.join(data_dir, "engine.ini"), f"""; Generated by tools/generate_car_data_full.py
[HEADER]
VERSION=1
POWER_CURVE=power.lut
COAST_CURVE=coast.lut

[ENGINE_DATA]
ALTITUDE_SENSITIVITY=0.1
INERTIA={v['engine_inertia']}
LIMITER={v['rpm_limit']}
LIMITER_HZ=18
MINIMUM={v['rpm_idle']}
DEFAULT_TURBO_BOOST=0.0

[COAST_REF]
RPM={v['rpm_limit']}
TORQUE={v['coast_torque']}
NON_LINEARITY=0

[ENGINE]
RPM_LIMIT_SAVE={v['rpm_limit']}

[DAMAGE]
MIN_RPM={v['rpm_idle']}
MAX_RPM={v['rpm_limit']}
ENGINE_BREAK_THRESHOLD=0.95
""")

    # coast.lut (engine braking torque across the rev range)
    coast_rows = []
    steps = 16
    for i in range(steps + 1):
        rpm = v["rpm_idle"] + (v["rpm_limit"] - v["rpm_idle"]) * i / steps
        # Coast torque rises with rpm, roughly 18% of peak torque at the limiter.
        torque = -v["coast_torque"] * (0.35 + 0.65 * i / steps)
        coast_rows.append(f"{int(rpm)}|{torque:.1f}")
    write(os.path.join(data_dir, "coast.lut"), "\n".join(coast_rows) + "\n")

    # power.lut
    write(os.path.join(data_dir, "power.lut"), power_lut(v))

    # drivetrain.ini
    gears = "\n".join(f"GEAR_{i}={g:.3f}" for i, g in enumerate(v["gears"], 1))
    write(os.path.join(data_dir, "drivetrain.ini"), f"""; Generated by tools/generate_car_data_full.py
[HEADER]
VERSION=1

[TRACTION]
TYPE={'FWD' if v.get('drivetrain_type') == 'FWD' else 'RWD'}

[GEARBOX]
CHANGE_UP_TIME={'250' if v['auto'] else '120'}
CHANGE_DN_TIME={'250' if v['auto'] else '120'}
SUPPORTS_SHIFTER=0

[GEARS]
{gears}
REVERSE={v['reverse']:.3f}
FINAL={v['final']:.3f}

[TRANSMISSION]
AUTOMATIC={'1' if v['auto'] else '0'}
AUTO_SHIFTER_UP={v['rpm_limit'] - 200}
AUTO_SHIFTER_DOWN={int(v['rpm_limit'] * 0.45)}
AUTO_CLUTCH=1

[CLUTCH]
MAX_TORQUE={int(v['torque_nm'] * 1.5)}
""")

    # suspensions.ini
    cg_loc = v.get("cg_front_pct", 0.55)
    arb_f = v["antiroll_f"]
    arb_r = v["antiroll_r"]
    write(os.path.join(data_dir, "suspensions.ini"), f"""; Generated by tools/generate_car_data_full.py
[HEADER]
VERSION=1

[BASIC]
WHEELBASE={v['wheelbase']:.3f}
CG_LOCATION={cg_loc:.2f}

[ARB]
FRONT={arb_f}
REAR={arb_r}

[FRONT]
TYPE={v['front_susp']}
BASEY={-v['cg_height'] / 2:.3f}
TRACK={v['track_f']:.3f}
ROD_LENGTH=0.075
HUB_MASS={int(v['mass'] * 0.06)}
TOE_OUT=0.0003
STATIC_CAMBER={v['camber_f']}
SPRING_RATE={v['front_spring']}
PROGRESSIVE_SPRING_RATE={int(v['front_spring'] * 0.25)}
BUMP_STOP_RATE={int(v['front_spring'] * 0.75)}
BUMPSTOP_UP=0.075
BUMPSTOP_DN=0.080
PACKER_RANGE=0.140
DAMP_BUMP={v['front_damper_bump']}
DAMP_FAST_BUMP={int(v['front_damper_bump'] * 0.55)}
DAMP_FAST_BUMPTHRESHOLD=0.100
DAMP_REBOUND={v['front_damper_rebound']}
DAMP_FAST_REBOUND={int(v['front_damper_rebound'] * 0.85)}
DAMP_FAST_REBOUNDTHRESHOLD=0.140

[REAR]
TYPE={v['rear_susp']}
BASEY={-v['cg_height'] / 2:.3f}
TRACK={v['track_r']:.3f}
ROD_LENGTH=0.060
HUB_MASS={int(v['mass'] * 0.05)}
TOE_OUT=0.00025
STATIC_CAMBER={v['camber_r']}
SPRING_RATE={v['rear_spring']}
PROGRESSIVE_SPRING_RATE={int(v['rear_spring'] * 0.15)}
BUMP_STOP_RATE={int(v['rear_spring'] * 1.0)}
BUMPSTOP_UP=0.055
BUMPSTOP_DN=0.070
PACKER_RANGE=0.130
DAMP_BUMP={v['rear_damper_bump']}
DAMP_FAST_BUMP={int(v['rear_damper_bump'] * 0.55)}
DAMP_FAST_BUMPTHRESHOLD=0.100
DAMP_REBOUND={v['rear_damper_rebound']}
DAMP_FAST_REBOUND={int(v['rear_damper_rebound'] * 0.85)}
DAMP_FAST_REBOUNDTHRESHOLD=0.140

[GEOMETRY]
WHEELBASE={v['wheelbase']:.3f}
CG_HEIGHT={v['cg_height']}
""")

    # tyres.ini
    sidewall = v["tyre_w"] * v["tyre_a"] / 100 / 1000
    diameter = v["rim"] * 0.0254 + 2 * sidewall
    radius = diameter / 2
    rim_radius = (v["rim"] * 0.0254) / 2 + 0.0127  # nominal rim + 0.5"
    width_m = v["tyre_w"] / 1000.0
    fz0 = v["tyre_load"]
    # Heavier vehicles need stiffer carcasses.
    heavy = v["tyre_load"] > 8000
    damp = 900 if heavy else 600
    rate = 620000 if heavy else 287000
    inertia = 2.6 if heavy else 1.36
    pressure_ideal = 62 if heavy else 39
    write(os.path.join(data_dir, "tyres.ini"), f"""; Generated by tools/generate_car_data_full.py
; Complete AC v10 tyre model (Pacejka-style combined slip)

[HEADER]
VERSION=10

[VIRTUALKM]
USE_LOAD=1

[COMPOUND_DEFAULT]
INDEX=0

[FRONT]
NAME=Street
SHORT_NAME=ST
WIDTH={width_m:.3f}
RADIUS={radius:.3f}
RIM_RADIUS={rim_radius:.3f}
ANGULAR_INERTIA={inertia}
DAMP={damp}
RATE={rate}
DY0=1.2267
DY1=-0.055
DX0=1.1847
DX1=-0.053
WEAR_CURVE=street_front.lut
SPEED_SENSITIVITY=0.003587
RELAXATION_LENGTH=0.07404
ROLLING_RESISTANCE_0={60 if heavy else 12}
ROLLING_RESISTANCE_1=0.001052
ROLLING_RESISTANCE_SLIP=5036
FLEX=0.000774
CAMBER_GAIN=0.157
DCAMBER_0=1.3
DCAMBER_1=-13
FRICTION_LIMIT_ANGLE=8.43
XMU=0.24
PRESSURE_STATIC={pressure_ideal - 7}
PRESSURE_SPRING_GAIN={14000 if heavy else 8357}
PRESSURE_FLEX_GAIN=0.5
PRESSURE_RR_GAIN=0.55
PRESSURE_D_GAIN=0.004
PRESSURE_IDEAL={pressure_ideal}
FZ0={fz0}
LS_EXPY=0.7442
LS_EXPX=0.8073
DX_REF=1.22
DY_REF=1.21
FLEX_GAIN=0.0304
FALLOFF_LEVEL=0.86
FALLOFF_SPEED=4
CX_MULT=1.02
RADIUS_ANGULAR_K=0.01
BRAKE_DX_MOD=0.02
THERMAL[0].PERFORMANCE_CURVE=0.65|0.88|1|1|1|0.98|0.70
THERMAL[0].SURFACE_TRANSFER=0.0012
THERMAL[0].INTERNAL_TRANSFER=0.00008
THERMAL[0].SURFACE_INERTIA=1000
THERMAL[0].INTERNAL_INERTIA=8000
THERMAL[0].COOL_FACTOR=0.10
THERMAL[0].SURFACE_ROLLING_FRICTION=0.03
THERMAL[1].PERFORMANCE_CURVE=0.65|0.88|1|1|1|0.98|0.70
THERMAL[1].SURFACE_TRANSFER=0.0012
THERMAL[1].INTERNAL_TRANSFER=0.00008
THERMAL[1].SURFACE_INERTIA=1000
THERMAL[1].INTERNAL_INERTIA=8000
THERMAL[1].COOL_FACTOR=0.10
THERMAL[1].SURFACE_ROLLING_FRICTION=0.03

[REAR]
NAME=Street
SHORT_NAME=ST
WIDTH={width_m:.3f}
RADIUS={radius:.3f}
RIM_RADIUS={rim_radius:.3f}
ANGULAR_INERTIA={inertia}
DAMP={damp}
RATE={rate}
DY0=1.2260
DY1=-0.055
DX0=1.1959
DX1=-0.053
WEAR_CURVE=street_rear.lut
SPEED_SENSITIVITY=0.003530
RELAXATION_LENGTH=0.07311
ROLLING_RESISTANCE_0={60 if heavy else 12}
ROLLING_RESISTANCE_1=0.001052
ROLLING_RESISTANCE_SLIP=5036
FLEX=0.000774
CAMBER_GAIN=0.157
DCAMBER_0=1.3
DCAMBER_1=-13
FRICTION_LIMIT_ANGLE=8.43
XMU=0.24
PRESSURE_STATIC={pressure_ideal - 7}
PRESSURE_SPRING_GAIN={14000 if heavy else 8357}
PRESSURE_FLEX_GAIN=0.5
PRESSURE_RR_GAIN=0.55
PRESSURE_D_GAIN=0.004
PRESSURE_IDEAL={pressure_ideal}
FZ0={fz0}
LS_EXPY=0.7442
LS_EXPX=0.8073
DX_REF=1.22
DY_REF=1.21
FLEX_GAIN=0.0304
FALLOFF_LEVEL=0.86
FALLOFF_SPEED=4
CX_MULT=1.02
RADIUS_ANGULAR_K=0.01
BRAKE_DX_MOD=0.02
THERMAL[0].PERFORMANCE_CURVE=0.65|0.88|1|1|1|0.98|0.70
THERMAL[0].SURFACE_TRANSFER=0.0012
THERMAL[0].INTERNAL_TRANSFER=0.00008
THERMAL[0].SURFACE_INERTIA=1000
THERMAL[0].INTERNAL_INERTIA=8000
THERMAL[0].COOL_FACTOR=0.10
THERMAL[0].SURFACE_ROLLING_FRICTION=0.03
THERMAL[1].PERFORMANCE_CURVE=0.65|0.88|1|1|1|0.98|0.70
THERMAL[1].SURFACE_TRANSFER=0.0012
THERMAL[1].INTERNAL_TRANSFER=0.00008
THERMAL[1].SURFACE_INERTIA=1000
THERMAL[1].INTERNAL_INERTIA=8000
THERMAL[1].COOL_FACTOR=0.10
THERMAL[1].SURFACE_ROLLING_FRICTION=0.03
""")

    # Wear + thermal LUTs referenced by tyres.ini
    wear_rows = []
    for i in range(11):
        x = i / 10
        # grip falls off as the tyre wears
        wear_rows.append(f"{x:.2f}|{1.0 - 0.25 * x * x:.4f}")
    wear_lut = "\n".join(wear_rows) + "\n"
    write(os.path.join(data_dir, "street_front.lut"), wear_lut)
    write(os.path.join(data_dir, "street_rear.lut"), wear_lut)

    # Analog speed curve (dash gauge calibration)
    speed_rows = []
    for i in range(21):
        kmh = i * 20
        speed_rows.append(f"{i}|{kmh}")
    write(os.path.join(data_dir, "analog_speed_curve.lut"), "\n".join(speed_rows) + "\n")

    # brakes.ini
    write(os.path.join(data_dir, "brakes.ini"), f"""; Generated by tools/generate_car_data_full.py
[FRONT]
DISC={v['brake_f']}
TYPE=VENTED_DISC

[REAR]
DISC={v['brake_r']}
TYPE={'DRUM' if v['rear_drum'] else 'DISC'}

[BIAS]
FRONT={v['brake_bias']:.2f}

[TORQUE]
MAX={v['brake_torque']}

[ABS]
ENABLED=1
""")

    # cameras.ini
    # AC requires FORWARD/UP/EXPOSURE; POSITION alone is ignored.
    ex, ey, ez = (v['driver_eyes'].split(",") + ["0", "1.1", "0"])[:3]
    write(os.path.join(data_dir, "cameras.ini"), f"""; Generated by tools/generate_car_data_full.py
[CAMERA_0]
NAME=DRIVER
POSITION={v['driver_eyes']}
FORWARD=0,-0.06,1
UP=0,1,0.06
FOV=55
EXPOSURE=28
EXTERNAL_SOUND=1

[CAMERA_1]
NAME=BUMPER
POSITION={v['bumper_cam']}
FORWARD=0,-0.05,1
UP=0,1,0.05
FOV=65
EXPOSURE=30
EXTERNAL_SOUND=1

[CAMERA_2]
NAME=BONNET
POSITION={v['bonnet_cam']}
FORWARD=0,-0.09,1
UP=0,1,0.09
FOV=62
EXPOSURE=30
EXTERNAL_SOUND=1

[CAMERA_3]
NAME=REAR
POSITION=0,1.15,{-float(v['length']) / 2 - 1.2:.2f}
FORWARD=0,-0.10,-1
UP=0,1,-0.10
FOV=60
EXPOSURE=30

[CAMERA_4]
NAME=CHASE
POSITION=0,2.4,{-float(v['length']) / 2 - 4.5:.2f}
FORWARD=0,-0.16,1
UP=0,1,0.16
FOV=58
EXPOSURE=30
""")

    # lights.ini
    write(os.path.join(data_dir, "lights.ini"), f"""; Generated by tools/generate_car_data_full.py
[HEADLIGHT]
POSITION=0,0.5,{v['length']/2:.2f}
COLOR=255,255,255
RANGE=80
SPOT=160

[BRAKELIGHT]
POSITION=0,0.5,{-v['length']/2:.2f}
COLOR=255,0,0
RANGE=20
SPOT=160

[INDICATOR_L]
POSITION={v['width']/2:.2f},0.5,{v['length']/2:.2f}
COLOR=255,165,0
RANGE=10
SPOT=160

[INDICATOR_R]
POSITION={-v['width']/2:.2f},0.5,{v['length']/2:.2f}
COLOR=255,165,0
RANGE=10
SPOT=160
""")

    # lods.ini
    write(os.path.join(data_dir, "lods.ini"), f"""; Generated by tools/generate_car_data_full.py
; AC requires FILE/IN/OUT, not NAME/DISTANCE.
; We ship a single body KN5, so one LOD covers the whole distance range.
[COCKPIT_HR]
DISTANCE_SWITCH=70

[LOD_0]
FILE={car_id}.kn5
IN=0
OUT=10000
""")

    # setup.ini
    write(os.path.join(data_dir, "setup.ini"), f"""; Generated by tools/generate_car_data_full.py
[DEFAULT]
TYRE_COMPOUND=street
FUEL=50
BRAKE_BIAS={v['brake_bias']:.2f}
""")

    # electronics.ini
    write(os.path.join(data_dir, "electronics.ini"), f"""; Generated by tools/generate_car_data_full.py
[ABS]
ENABLED=1

[TC]
ENABLED=1

[ESC]
ENABLED=1
""")

    # ai.ini
    # AC reads GEARS/PEDALS/LOOKAHEAD/STEER; a bare [AI] block is ignored.
    write(os.path.join(data_dir, "ai.ini"), f"""; Generated by tools/generate_car_data_full.py
[HEADER]
VERSION=3

[GEARS]
UP={int(v['rpm_limit'] * 0.94)}
DOWN={int(v['rpm_limit'] * 0.62)}
SLIP_THRESHOLD=0.95
GAS_CUTOFF_TIME=0.30

[PEDALS]
GASGAIN=4.0
BRAKE_HINT=1
TRAIL_HINT=0.3

[LOOKAHEAD]
BASE=19
SPEED_GAIN=0.10
GAS_BRAKE_LOOKAHEAD=0

[STEER]
STEER_GAIN=1.78

[ULTRA_GRIP]
VALUE=1.2

[PHYSICS_HINTS]
AERO_HINT=1
""")

    # colliders.ini
    write(os.path.join(data_dir, "colliders.ini"), f"""; Generated by tools/generate_car_data_full.py
[COLLIDER]
POSITION=0,0,0
SIZE={v['length']:.2f},{v['width']:.2f},{v['height']:.2f}
""")

    # driver3d.ini
    write(os.path.join(data_dir, "driver3d.ini"), f"""; Generated by tools/generate_car_data_full.py
[DRIVER]
POSITION={v['driver_eyes']}
""")

    # mirrors.ini
    write(os.path.join(data_dir, "mirrors.ini"), f"""; Generated by tools/generate_car_data_full.py
[MIRROR_L]
POSITION={v['width']/2:.2f},1.0,-1.0
SIZE=0.3,0.2

[MIRROR_R]
POSITION={-v['width']/2:.2f},1.0,-1.0
SIZE=0.3,0.2
""")

    # sounds.ini
    # AC reads SKIDS/WIND/Gearbox etc.; the old [SOUNDS] block did nothing.
    write(os.path.join(data_dir, "sounds.ini"), f"""; Generated by tools/generate_car_data_full.py
[SKIDS]
ENTRY_POINT=0.45
MIX_VOLUME=0.6
PITCH_BASE=0.58
PITCH_GAIN=0.18

[WIND]
SPEED_GAIN_0=0
SPEED_GAIN_1=0.0003
VOLUME_GAIN=0.7

[Gearbox]
VOLUME=1.0
""")

    # aero.ini
    write(os.path.join(data_dir, "aero.ini"), f"""; Generated by tools/generate_car_data_full.py
[AERO]
DRAG_COEFF={v['aero_drag']}
FRONT_AREA={v['length']*v['width']:.2f}
FRONT_DOWNFORCE={v['aero_front']}
REAR_DOWNFORCE={v['aero_rear']}
""")

    # damage.ini
    write(os.path.join(data_dir, "damage.ini"), f"""; Generated by tools/generate_car_data_full.py
[DAMAGE]
FRONT=1.0
REAR=1.0
LEFT=1.0
RIGHT=1.0
TOP=1.0
BOTTOM=1.0
""")

    # fuel_cons.ini
    write(os.path.join(data_dir, "fuel_cons.ini"), f"""; Generated by tools/generate_car_data_full.py
[FUEL]
CONSUMPTION={v['fuel_consumption']}
""")

    # ambient_shadows.ini
    write(os.path.join(data_dir, "ambient_shadows.ini"), f"""; Generated by tools/generate_car_data_full.py
[SHADOW]
SIZE={v['length']:.2f},{v['width']:.2f}
""")

    # analog_instruments.ini
    write(os.path.join(data_dir, "analog_instruments.ini"), f"""; Generated by tools/generate_car_data_full.py
[SPEEDOMETER]
MAX=200
POSITION=0.5,0.5

[TACHOMETER]
MAX={v['rpm_limit']}
POSITION=0.5,0.5
""")

    # digital_instruments.ini
    write(os.path.join(data_dir, "digital_instruments.ini"), f"""; Generated by tools/generate_car_data_full.py
[SPEEDOMETER]
MAX=200
POSITION=0.5,0.5

[TACHOMETER]
MAX={v['rpm_limit']}
POSITION=0.5,0.5
""")

    # dash_cam.ini
    write(os.path.join(data_dir, "dash_cam.ini"), f"""; Generated by tools/generate_car_data_full.py
[DASH_CAM]
POSITION=0,0.5,0.5
""")

    # suspension_graphics.ini
    write(os.path.join(data_dir, "suspension_graphics.ini"), "")

    # escmode.ini
    write(os.path.join(data_dir, "escmode.ini"), f"""; Generated by tools/generate_car_data_full.py
[ESC]
MODE=1
""")

    # blurred_objects.ini
    write(os.path.join(data_dir, "blurred_objects.ini"), "")

    # LUT files
    write(os.path.join(data_dir, "street_front.lut"), street_lut(v))
    write(os.path.join(data_dir, "street_rear.lut"), street_lut(v))
    write(os.path.join(data_dir, "street90_front.lut"), street_lut(v))
    write(os.path.join(data_dir, "street90_rear.lut"), street_lut(v))
    write(os.path.join(data_dir, "tcurve_street.lut"), tcurve_lut(v))
    write(os.path.join(data_dir, "tcurve_street90.lut"), tcurve_lut(v))
    write(os.path.join(data_dir, "throttle.lut"), throttle_lut(v))

    print(f"  [OK] {car_id}: {len(os.listdir(data_dir))} data files")


def main() -> None:
    count = 0
    for car_id, v in VEHICLES.items():
        generate_car(car_id, v)
        count += 1
    print(f"[DONE] Generated complete data for {count} vehicles.")


if __name__ == "__main__":
    main()
