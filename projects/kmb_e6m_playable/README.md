# KMB E6M Assetto Corsa local prototype configurations

Small configuration companion for the locally converted `kmb_e6m_drivable` bus. This is not a complete car download. Merge `content/` with the matching updated local build after backing it up. The cockpit configuration requires the newly patched KN5 with the KMB motion/LCD nodes; an older model alone will not provide them.

The model, textures, destination bitmaps, animations and sound bank remain local. The route skins reference existing local OMSI-derived artwork. Do not expect these text files to create a car or signs by themselves.

The update adds three mirror glass bindings, cockpit telemetry and supported clickable controls, source-derived gauge curves, and six F6 camera views. The third axle has CSP visual wheel rotation; AC physics still models two axles. To set a route from the local OMSI HOF and bitmap files, use `tools/set_kmb_bus_display.py e6m`; see `../kmb_bus_tools/README.md` for the steps. The original four bundled skins remain available as defaults/examples.

See `../kmb_bus_tools/TEST_DRIVE.md` for testing and limits, and the tools project for model-patching helpers. The local build passed structural checks, offline Blender view review, and Lua tests using mocked CSP APIs. Live AC mirrors, instruments, controls and handling remain for user testing.

OMSI passengers, doors, ticketing, keypad, full electrical/air and exterior lighting systems are not ported. No original OMSI assets are included here.
