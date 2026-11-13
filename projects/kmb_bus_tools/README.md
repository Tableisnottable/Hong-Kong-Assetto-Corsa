# Local OMSI to AC bus helpers

Tools used for the local E6M/E200 cockpit, destination and camera update. These scripts expect this project layout: `work/` for helpers and source dependencies, `outputs/E200_playable/content/cars/kmb_e200_drivable/` and `outputs/E6M_playable/content/cars/kmb_e6m_drivable/` for generated cars. Original source models and the generated KN5 files are not included. The scripts retain local Windows installation paths and require adaptation on another machine.

Python dependencies: NumPy and Pillow; optional test dependency Lupa. Blender 5.1 runs the offline preview scripts. Build/import helpers also require the separately obtained O3D importer and local source/donor assets described in their code. No third-party dependency tree is checked in. The installed CSP Lua SDK was the API reference (local version 0.2.11).

`patch_bus_cockpits.py`, `finish_cockpit_bindings.py`, and camera/seat adjustment scripts operate on a specific build stage. They are one-time migrations, not idempotent repair commands: back up the current KN5 and check the expected nodes before running them. Repeating them can duplicate pivots or move geometry twice. The source files document the expected baseline.

For a matching local build, run `python work/validate_playable.py E200`, the same for `E6M`, and `python work/test_cockpit_runtime.py` after making Lupa available under `work/test_runtime` or on Python's import path. `prepare_chase_camera.py` derives the scoped chase variant from the locally installed CSP base camera. `test_bus_chase_camera.py` exercises its stationary view positions and checks that other car IDs retain the original placement. Blender's `check_bus_views.py -- E200` (or E6M) renders the car-local views and nominal chase positions. Offline scripts do not launch AC.

The shared chase implementation goes in AC's `extension/lua/chaser-camera/kmb_bus_base/camera.lua`, with the user CSP `chaser_camera.ini` setting `[BASIC] IMPLEMENTATION=kmb_bus_base`. It preserves base behavior for other car IDs. Real mirrors require the user CSP `smart_mirror.ini` setting `[REAL_MIRRORS] ENABLED=1`; `ONLY_WITHOUT_VIRTUAL=0` keeps visible physical mirrors active alongside the virtual mirror. Back up shared settings before changing them.

See TEST_DRIVE.md for installed behavior and remaining runtime checks. Large models, textures, sounds, binary animations, source archives, backups and render outputs are intentionally omitted.
