# OMSI Bus Conversion

`tools/build_omsi_families.py` converts the installed OMSI O3D body and wheel meshes for the KMB ATENU, ATEE, Dennis Dragon, and Scania families into local Assetto Corsa packages. It reads mass and the full engine torque curve from each source `.bus` and engine constant file, then uses the named installed AC bus as the starting physics and sound package.

The converter expects OMSI 2 at `A:\SteamLibrary\steamapps\common\OMSI 2\Vehicles`, Assetto Corsa at `A:\SteamLibrary\steamapps\common\assettocorsa`, and Python packages `numpy` and `Pillow`. Run one family at a time from the repository root:

```powershell
python tools/build_omsi_families.py atenu
python tools/build_omsi_families.py atee
python tools/build_omsi_families.py dragon
python tools/build_omsi_families.py scania
```

Packages are written to `outputs/<FAMILY>_playable/`. The script does not install them. Copy each resulting car folder from `content/cars/` into the AC `content/cars/` directory after closing AC. Large converted KN5 models, source textures, and sound banks are local outputs and are intentionally not tracked in this repository.

The two rear axles on three-axle models use the middle axle for native AC physics; the final axle rotates through a Custom Shaders Patch Lua animation. Gearbox, suspension detail, mirrors, cockpit controls, and sounds come from the AC donor package and are adaptations, not a port of OMSI scripts. In-game driving still needs to be tested on the target installation.
