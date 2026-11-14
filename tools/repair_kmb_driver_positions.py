"""Place the posed native AC driver in each converted OMSI cab.

Uses the installed E6M's full seated skeleton and steering animation, rather
than the unrelated donor bus's four-node placement file. Close AC to install.
"""
import argparse
import datetime
import io
import json
from pathlib import Path
import shutil
import struct

import numpy as np
from kn5_tools import read_string, read_u32
from repair_omsi_bus_physics import AC, ini, save, set_values

FAMILIES = ("atenu", "atee", "dennis_dragon_9m", "scania_k230ub")


def skeleton(raw):
    stream = io.BytesIO(raw)
    result = {}

    def read(parent=np.eye(4)):
        name = read_string(stream)
        offset = stream.tell()
        local = np.frombuffer(stream.read(64), "<f4").reshape(4, 4)
        world = local @ parent
        result[name] = (offset, world.copy())
        for _ in range(read_u32(stream)):
            read(world)

    read()
    if stream.tell() != len(raw):
        raise ValueError("Unexpected KNH trailing data")
    return result


def translate_pose(raw, delta):
    data = bytearray(raw)
    bones = skeleton(data)
    offset, _ = bones["DRIVER:DRIVER"]
    np.frombuffer(data, "<f4", 3, offset + 48)[:] += delta
    return bytes(data)


def translate_animation(raw, delta):
    data = bytearray(raw)
    stream = io.BytesIO(data)
    version, count = struct.unpack("<ii", stream.read(8))
    if version != 2:
        raise ValueError("Expected KSANIM version 2")
    for _ in range(count):
        name, frames = read_string(stream), read_u32(stream)
        offset = stream.tell()
        if name == "DRIVER:DRIVER":
            values = np.ndarray((frames, 10), "<f4", buffer=data, offset=offset)
            values[:, 4:7] += delta
        stream.seek(frames * 40, 1)
    if stream.tell() != len(data):
        raise ValueError("Unexpected KSANIM trailing data")
    return bytes(data)


def configure_driver(car, reference, backup):
    car, reference, backup = map(Path, (car, reference, backup))
    if car.resolve() == reference.resolve():
        raise ValueError("Reference driver must remain read-only")
    original = (reference / "driver_base_pos.knh").read_bytes()
    bones = skeleton(original)
    if len(bones) < 50:
        raise ValueError("Reference must contain a full posed driver skeleton")
    eyes = np.array(list(map(float, ini(car / "data/car.ini")["GRAPHICS"]["DRIVEREYES"].split(","))))
    # Match the successful E6M seating convention: head joint slightly below
    # and behind the driver's eye. Camera coordinates already use AC's CG frame.
    target = eyes + np.array([0, -.10, -.07])
    delta = target - bones["DRIVER:RIG_Head"][1][3, :3]
    updates = {"driver_base_pos.knh": translate_pose(original, delta)}
    for name in ("steer.ksanim", "shift.ksanim", "shift_dw.ksanim"):
        path = reference / "animations" / name
        if path.exists():
            updates["animations/" + name] = translate_animation(path.read_bytes(), delta)
    check = skeleton(updates["driver_base_pos.knh"])
    head = check["DRIVER:RIG_Head"][1][3, :3]
    if not np.allclose(head, target, atol=1e-5):
        raise ValueError("Driver translation did not reach the intended head position")
    for rel, data in updates.items():
        path = car / rel
        if path.exists() and path.read_bytes() == data:
            continue
        if path.exists():
            dest = backup / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    cp = ini(reference / "data/driver3d.ini")
    set_values(cp, "MODEL", {"POSITION": "0,0,0"})
    path = car / "data/driver3d.ini"
    dest = backup / "data/driver3d.ini"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not dest.exists():
        shutil.copy2(path, dest)
    save(cp, path)
    return {"car": car.name, "eyes": eyes.tolist(), "head": head.tolist(),
            "hips": check["DRIVER:RIG_Hips"][1][3, :3].tolist(), "bones": len(check),
            "reference": str(reference), "backup": str(backup),
            "runtime": "Pending user check; hands retain the adapted E6M pose"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ac", type=Path, default=AC)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import subprocess
    running = subprocess.run(["tasklist", "/FI", "IMAGENAME eq acs.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True)
    if '"acs.exe"' in running.stdout.lower():
        raise SystemExit("Close AC before changing driver poses")
    cars = args.ac / "content/cars"
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results = [configure_driver(cars / f"kmb_{family}_drivable", cars / "kmb_e6m_drivable",
               args.output / "backups" / stamp / family) for family in FAMILIES]
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "driver_positions.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
