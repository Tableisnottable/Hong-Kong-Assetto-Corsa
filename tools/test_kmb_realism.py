"""Pure config-mapping tests for OMSI-derived KMB AC physics settings."""
import configparser
import unittest

from repair_omsi_bus_physics import (
    apply_source_powertrain, apply_source_suspension, source_forward_ratios, source_limiter,
)


def cp(text):
    result = configparser.ConfigParser(interpolation=None)
    result.optionxform = str
    result.read_string(text)
    return result


def source(curve=None, gearbox=None, engine=None, axles=None):
    return {
        "curve": curve or [(700, 400), (1200, 800), (2000, 500)],
        "gear_constants": gearbox or {"antrieb_getr_ratio1": 3.0, "antrieb_getr_ratio2": 1.5,
            "antrieb_i_achse": 5.0, "antrieb_gangwahlzeit": .5},
        "engine_constants": engine or {"engine_J": 4.0, "engine_governed_idle_RPM": 700},
        "axles": axles or [
            {"achse_long": 3, "achse_feder": 240, "achse_daempfer": 20},
            {"achse_long": -2, "achse_feder": 280, "achse_daempfer": 18},
            {"achse_long": -3, "achse_feder": 150, "achse_daempfer": 16},
        ],
    }


class KmbRealismConfigTests(unittest.TestCase):
    def test_limiter_prefers_hard_source_limit_and_never_exceeds_curve(self):
        spec = source(curve=[(700, 200), (1900, 500), (2400, 0)],
                      engine={"engine_J": 3.5, "engine_maxrpm": 2500})
        self.assertEqual(source_limiter(spec), 2400)
        spec["engine_constants"].pop("engine_maxrpm")
        spec["gear_constants"]["antrieb_overrev_protection_rpm"] = 2350
        self.assertEqual(source_limiter(spec), 2350)

    def test_ratios_are_sorted_and_dragon_converter_first_is_preserved(self):
        spec = source(gearbox={"antrieb_getr_ratio3": 1.0, "antrieb_getr_ratio1": 1.36,
                              "antrieb_getr_ratio2": 1.36})
        self.assertEqual(source_forward_ratios(spec, "standard"), [1.36, 1.36, 1.0])
        self.assertEqual(source_forward_ratios(spec, "dragon", 3.0), [3.0, 1.36, 1.0])
        with self.assertRaises(ValueError):
            source_forward_ratios(spec, "dragon")

    def test_powertrain_maps_source_fields_and_shift_time(self):
        spec = source(curve=[(700, 400), (1800, 800), (2200, 0)],
                      gearbox={"antrieb_getr_ratio1": 1.36, "antrieb_getr_ratio2": 1.36,
                               "antrieb_getr_ratio3": 1.0, "antrieb_i_achse": 5.38,
                               "antrieb_gangwahlzeit": .5},
                      engine={"engine_J": 4.5, "engine_governed_idle_RPM": 700,
                              "rpmgov": 2150})
        engine = cp("[ENGINE_DATA]\nINERTIA=1\nLIMITER=3000\nMINIMUM=500\n")
        drive = cp("[GEARS]\nCOUNT=3\nGEAR_R=-4\nGEAR_1=2.4\nGEAR_2=1\nGEAR_3=.5\nFINAL=4\n\n[GEARBOX]\nCHANGE_UP_TIME=200\n\n[AUTO_SHIFTER]\nGAS_CUTOFF_TIME=.1\n")
        report = apply_source_powertrain(engine, drive, spec, "standard")
        self.assertEqual(report["limiter_rpm"], 2150)
        self.assertEqual(engine["ENGINE_DATA"]["INERTIA"], "4.5")
        self.assertEqual(drive["GEARS"]["GEAR_1"], "1.36")
        self.assertEqual(drive["GEARS"]["FINAL"], "5.38")
        self.assertEqual(drive["GEARBOX"]["CHANGE_UP_TIME"], "500")
        self.assertEqual(drive["GEARBOX"]["CHANGE_DN_TIME"], "500")
        self.assertEqual(drive["AUTO_SHIFTER"]["GAS_CUTOFF_TIME"], "0.50")

    def test_triaxle_rates_and_static_loads_map_to_ac_contact_groups(self):
        spec = source()
        suspension = cp("[BASIC]\nCG_LOCATION=.5\n\n[FRONT]\nHUB_MASS=170\n\n[REAR]\nHUB_MASS=300\n")
        tyres = cp("[FRONT]\n\n[REAR]\n")
        apply_source_suspension(suspension, tyres, spec, "standard", 14800, .5, .5)
        self.assertEqual(float(suspension["FRONT"]["SPRING_RATE"]), 240000)
        self.assertEqual(float(suspension["REAR"]["SPRING_RATE"]), 430000)
        self.assertEqual(float(suspension["REAR"]["DAMP_BUMP"]), 34000)
        self.assertEqual(float(suspension["FRONT"]["HUB_MASS"]), 170)
        self.assertEqual(float(suspension["REAR"]["HUB_MASS"]), 300)
        front_per_wheel = float(tyres["FRONT"]["FZ0"]) / 9.81
        rear_per_wheel = float(tyres["REAR"]["FZ0"]) / 9.81
        self.assertAlmostEqual(2 * (front_per_wheel + rear_per_wheel), 14800, delta=1)
        self.assertAlmostEqual(front_per_wheel / rear_per_wheel, 240 / 430, delta=.001)
        self.assertNotEqual(tyres["FRONT"]["FZ0"], tyres["REAR"]["FZ0"])

    def test_scania_maps_only_its_converted_rear_contact_axle(self):
        spec = source(axles=[
            {"achse_long": 3, "achse_feder": 240, "achse_daempfer": 20},
            {"achse_long": -2, "achse_feder": 280, "achse_daempfer": 18},
            {"achse_long": -3, "achse_feder": 1000, "achse_daempfer": 100},
        ])
        suspension = cp("[BASIC]\n\n[FRONT]\nHUB_MASS=120\n\n[REAR]\nHUB_MASS=220\n")
        tyres = cp("[FRONT]\n\n[REAR]\n")
        apply_source_suspension(suspension, tyres, spec, "scania", 10000, .47, .48)
        self.assertEqual(float(suspension["REAR"]["SPRING_RATE"]), 280000)
        self.assertEqual(float(suspension["REAR"]["DAMP_BUMP"]), 18000)
        self.assertEqual(float(tyres["FRONT"]["FZ0"]), 22638)
        self.assertEqual(float(tyres["REAR"]["FZ0"]), 26412)


if __name__ == "__main__":
    unittest.main()
