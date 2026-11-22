"""Sample calibrated KMB speed curves against source knots and shared speed input."""
import unittest
import json
import math
import re
from pathlib import Path

from repair_kmb_speedometers import (
    AC, BUSES, LUA_GAUGE_CARS, ROOT, curve_text, destinations, interpolate,
)


def read_lut(path: Path):
    points = []
    for line in path.read_text(encoding="ascii").splitlines():
        if line.strip():
            speed, angle = line.split("|", 1)
            points.append((float(speed), float(angle)))
    return tuple(points)


def read_lua_curve(path: Path):
    source = path.read_text(encoding="utf-8")
    match = re.search(r'\["speedCurve"\]=(\{\{.*?\}\})', source)
    if match is None:
        raise AssertionError(f"No embedded speedCurve in {path}")
    return json.loads(match.group(1).replace("{", "[").replace("}", "]"))


class SpeedometerCalibrationTests(unittest.TestCase):
    def test_bus_set_matches_planner_configuration(self):
        root = Path(__file__).resolve().parent.parent
        config = json.loads((root / "config/kmb_ai_buses.json").read_text(encoding="utf-8"))
        self.assertEqual({bus["id"] for bus in config["buses"]}, set(BUSES))

    def test_source_knots_are_preserved(self):
        for car_id, (_, curve, _) in BUSES.items():
            with self.subTest(car=car_id):
                for speed, expected_angle in curve:
                    self.assertAlmostEqual(interpolate(curve, speed), expected_angle, places=8)

    def test_sampled_needle_is_monotonic_and_bounded(self):
        for car_id, (_, curve, _) in BUSES.items():
            with self.subTest(car=car_id):
                previous = -1.0
                for step in range(-500, 501):
                    vehicle_speed_kmh = step / 4
                    shared_speed_kmh = abs(vehicle_speed_kmh)
                    digital_kmh = math.floor(shared_speed_kmh + 0.5)
                    angle = interpolate(curve, shared_speed_kmh)
                    self.assertEqual(digital_kmh, math.floor(abs(vehicle_speed_kmh) + 0.5))
                    self.assertGreaterEqual(angle, curve[0][1])
                    self.assertLessEqual(angle, curve[-1][1])
                    if vehicle_speed_kmh >= 0:
                        self.assertGreaterEqual(angle, previous)
                        previous = angle
                self.assertEqual(len(curve_text(curve).splitlines()), len(curve))

    def test_installed_luts_and_lua_curves_match_calibration(self):
        for car_id, (_, curve, _) in BUSES.items():
            with self.subTest(car=car_id):
                car = AC / "content/cars" / car_id
                actual = read_lut(car / "data/analog_speed_curve.lut")
                raw_lut = (car / "data/analog_speed_curve.lut").read_text(encoding="ascii")
                self.assertEqual(len(raw_lut.splitlines()), len(actual))
                self.assertEqual(len(actual), len(curve))
                for actual_point, source_point in zip(actual, curve):
                    self.assertAlmostEqual(actual_point[0], source_point[0], places=6)
                    self.assertAlmostEqual(actual_point[1], source_point[1], places=5)
                binding_path = car / "extension/cockpit_bindings.json"
                if binding_path.is_file():
                    binding = json.loads(binding_path.read_text(encoding="utf-8"))
                    self.assertEqual(binding["speedCurve"], [list(point) for point in curve])
                cockpit_path = car / "extension/cockpit.lua"
                if car_id in LUA_GAUGE_CARS:
                    self.assertTrue(cockpit_path.is_file())
                    cockpit = cockpit_path.read_text(encoding="utf-8")
                    self.assertEqual(read_lua_curve(cockpit_path), [list(point) for point in curve])
                    self.assertIn("math.abs(car.speedKmh)", cockpit)
                    self.assertIn("math.floor(velocity + 0.5)", cockpit)

    def test_source_luts_match_calibration(self):
        sources = {
            car_id: path
            for car_id, _, path, kind in destinations(AC, ROOT, True)
            if kind == "source"
        }
        for car_id, (_, curve, _) in BUSES.items():
            with self.subTest(car=car_id):
                self.assertIn(car_id, sources)
                actual = read_lut(sources[car_id])
                self.assertEqual(len(actual), len(curve))
                for actual_point, source_point in zip(actual, curve):
                    self.assertAlmostEqual(actual_point[0], source_point[0], places=6)
                    self.assertAlmostEqual(actual_point[1], source_point[1], places=5)

    def test_source_lua_curve_matches_its_calibration(self):
        sources = {
            car_id: (curve, path)
            for car_id, curve, path, kind in destinations(AC, ROOT, True)
            if kind == "source-cockpit"
        }
        for car_id, (_, curve, _) in BUSES.items():
            source = sources.get(car_id)
            if source is None:
                continue
            with self.subTest(car=car_id):
                self.assertEqual(source[0], curve)
                self.assertEqual(read_lua_curve(source[1]), [list(point) for point in curve])

    def test_source_specific_reference_values(self):
        self.assertAlmostEqual(interpolate(BUSES["kmb_e200_drivable"][1], 60), 112)
        self.assertAlmostEqual(interpolate(BUSES["kmb_atenu_drivable"][1], 60), 112)
        self.assertAlmostEqual(interpolate(BUSES["kmb_dennis_dragon_9m_drivable"][1], 20), 30)
        self.assertAlmostEqual(interpolate(BUSES["kmb_dennis_dragon_9m_drivable"][1], 60), 115)
        self.assertAlmostEqual(interpolate(BUSES["kmb_scania_k230ub_drivable"][1], 20), 12.4)
        self.assertAlmostEqual(interpolate(BUSES["kmb_scania_k230ub_drivable"][1], 110), 248)


if __name__ == "__main__":
    unittest.main()
