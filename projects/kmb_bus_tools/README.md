# Local OMSI to AC bus helpers

Tools used for the local E6M/E200 cockpit, destination and camera update. The original source models and generated KN5 files are not included. Python dependencies: NumPy and Pillow; optional test dependency Lupa. Blender 5.1 runs offline preview scripts. Build/import helpers also require the separately obtained O3D importer and local source/donor assets described in their code. No third-party dependency tree is checked in. The installed CSP Lua SDK was the API reference (local version 0.2.11).

The patch scripts operate on specific build stages. They are one-time migrations, not idempotent repair commands: back up the current KN5 and check expected nodes before running them. From the repository root, for matching local builds, run `python projects/kmb_bus_tools/work/validate_playable.py E200`, the same for `E6M`, and `python projects/kmb_bus_tools/work/test_cockpit_runtime.py` after making Lupa available. Offline scripts do not launch AC.

The shared chase implementation goes in AC's `extension/lua/chaser-camera/kmb_bus_base/camera.lua`, with the user CSP `chaser_camera.ini` setting `[BASIC] IMPLEMENTATION=kmb_bus_base`. Real mirrors require the user CSP `smart_mirror.ini` setting `[REAL_MIRRORS] ENABLED=1`. Back up shared settings before changing them.

## Set a route display

The buses use the original OMSI `KMB_AllRoutes_Full.hof` destination names and Hanover bitmap artwork. A small updater keeps one reusable `KMB CUSTOM` skin per bus, so the many routes do not become thousands of Content Manager skins.

1. Close Assetto Corsa.
2. Make sure Python 3, NumPy and Pillow are available (`python -m pip install numpy Pillow` if needed).
3. Double-click `tools/set_kmb_bus_display.cmd`, then choose one bus or **all**. Alternatively run `python tools/set_kmb_bus_display.py all`.
4. Enter a route number or destination search text. If the route has several termini, select the matching destination from the numbered results. The installed full HOF currently contains 1,674 route/terminus entries.
5. Open Content Manager, refresh the selected car's skins, and choose `KMB CUSTOM | route | destination` before starting a session.

Supported bus names are `e200`, `e6m`, `atenu`, `atee`, `scania`, and `dragon`. Use `--list` after the bus name to list all entries with a stable one-based index without changing the AC install. Then apply any entry to all six buses with `python tools/set_kmb_bus_display.py all --entry NUMBER`, or search with `python tools/set_kmb_bus_display.py all --query "route or destination"`. Each run updates the reusable `KMB CUSTOM` skin on every bus with the selected terminus. Use `--hof PATH` to select another OMSI HOF file. The utility reads files from the default OMSI and AC paths on drive A; edit the constants at the top of the script if those folders are elsewhere.

The updater uses each family's artwork and actual panel proportions: E200/ATENU amber, E6M white, ATEE/Scania green, Dragon printed rollblinds. E6M NIS also uses the white OMSI atlas. It writes front/side/rear textures into `skins/kmb_custom_route` (Dragon has separate number boards). Route text and destination names come from HOF data, so availability depends on that file. Missing matching artwork uses a documented shared OMSI bitmap or rendered HOF text; Scania's absent Gorba library and unsupported Dragon destinations remain adaptations. Generated files, backups and source records go under the user's `Documents/Assetto Corsa/kmb_tools/displays` folder by default.

Native AC opponents select the route skin like the player. Traffic Planner embeds its textures in separate models: after selecting a custom route, close AC and run `python tools/build_kmb_planner_traffic.py --skin kmb_custom_route --output <local-output-folder> --install`. Apply the custom route to **all** buses first. This remains pre-session skin selection; the OMSI destination keypad is not ported.

## Bus coverage

These helpers cover the E200 and E6M local prototypes. The local installation now also contains ATENU, ATEE, Dennis Dragon 9.9M and Scania K230UB conversion prototypes; see [the installed lineup and conversion guide](../../docs/omsi_bus_conversion.md) for their separate build and physics-repair workflow. Their in-game driving still needs verification. Do not apply an E200/E6M model-stage patch to another family. AI-only OMSI variants are not included in the player-bus list. No OMSI source assets are stored in this repository.

See `TEST_DRIVE.md` for installed behavior and remaining runtime checks. Large models, textures, sounds, binary animations, source archives, backups and render outputs are intentionally omitted. The missing-parts migration `repair_bus_missing_parts.py` restores the native HUB/WHEEL/SUSP hierarchy and E200 identity/glazing. The local user had disabled CSP Car Instruments; `[BASIC] ENABLED=1` in the user `cfg/extension/car_instruments.ini` is required for tag-wheel and cockpit Lua.
