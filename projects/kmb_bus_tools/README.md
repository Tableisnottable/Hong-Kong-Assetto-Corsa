# Local OMSI to AC bus helpers

Tools used for the local E6M/E200 cockpit, destination and camera update. The original source models and generated KN5 files are not included. Python dependencies: NumPy and Pillow; optional test dependency Lupa. Blender 5.1 runs offline preview scripts. Build/import helpers also require the separately obtained O3D importer and local source/donor assets described in their code. No third-party dependency tree is checked in. The installed CSP Lua SDK was the API reference (local version 0.2.11).

The patch scripts operate on specific build stages. They are one-time migrations, not idempotent repair commands: back up the current KN5 and check expected nodes before running them. For matching local builds, run `python work/validate_playable.py E200`, the same for `E6M`, and `python work/test_cockpit_runtime.py` after making Lupa available. Offline scripts do not launch AC.

The shared chase implementation goes in AC's `extension/lua/chaser-camera/kmb_bus_base/camera.lua`, with the user CSP `chaser_camera.ini` setting `[BASIC] IMPLEMENTATION=kmb_bus_base`. Real mirrors require the user CSP `smart_mirror.ini` setting `[REAL_MIRRORS] ENABLED=1`. Back up shared settings before changing them.

## Set a route display

The buses use the original OMSI `KMB_AllRoutes_Full.hof` destination names and Hanover bitmap artwork. A small updater keeps one reusable `KMB CUSTOM` skin per bus, so the many routes do not become thousands of Content Manager skins.

1. Close Assetto Corsa.
2. Make sure Python 3 and Pillow are available (`python -m pip install Pillow` if needed).
3. From this repository, run `python tools/set_kmb_bus_display.py e200` or `python tools/set_kmb_bus_display.py e6m`.
4. Enter a route number or destination search text. If the route has several termini, select the matching destination from the numbered results.
5. Open Content Manager, refresh the selected car's skins, and choose `KMB CUSTOM | route | destination` before starting a session.

Use `--list` after the bus name to list all entries without changing the AC install. Use `--hof PATH` to select another OMSI HOF file. The utility reads files from the default OMSI and AC paths on drive A; edit the constants at the top of the script if those folders are elsewhere.

The updater uses the original display bitmap and writes three DDS files into that car's `skins/kmb_custom_route` folder. Route text and destination names come from HOF data, so route availability depends on the selected HOF file. Some entries use non-Hanover or script-generated displays and may not have a standalone bitmap in the KMBVC folder.

## Bus coverage

The installed E200 and E6M conversions are drivable AC prototypes. OMSI models in other families need separate geometry, wheel, cockpit, sound and physics work before they can be described as playable. AI-only OMSI variants are not included in the player-bus list. No OMSI source assets are stored in this repository.

See `TEST_DRIVE.md` for installed behavior and remaining runtime checks. Large models, textures, sounds, binary animations, source archives, backups and render outputs are intentionally omitted. The missing-parts migration `repair_bus_missing_parts.py` restores the native HUB/WHEEL/SUSP hierarchy and E200 identity/glazing. The local user had disabled CSP Car Instruments; `[BASIC] ENABLED=1` in the user `cfg/extension/car_instruments.ini` is required for tag-wheel and cockpit Lua.
