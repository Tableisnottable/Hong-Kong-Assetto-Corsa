# E200 and E6M local test build

The updated cars are installed in `A:/SteamLibrary/steamapps/common/assettocorsa/content/cars/` as `kmb_e200_drivable` and `kmb_e6m_drivable`. Restart the driving session to load the changed models, cameras and CSP scripts. Refresh Content Manager's car/skin list if its thumbnails remain cached.

## Test in AC

1. Select either bus and a destination skin: Not in Service, 51 Tai Mo Shan, 51 Sheung Tsuen, or 51 Nina Tower. The signs use the local OMSI bitmaps. Tai Mo Shan is the mountain icon and 大帽山 / 巔峰之旅 51 artwork.
2. Check the cockpit, dashboard/bonnet, bumper, both chase cameras, left/right glances and look-back. F6 cycles the six car-local views: driver, clear rear view, front exterior, left exterior, right exterior, rear exterior. E200's driver view and seat are 30 cm farther back.
3. Check all three mirrors with scenery behind you. CSP Real Mirrors is enabled. Offline preview images show a dark mirror fallback because Blender cannot render AC's live mirror textures.
4. Drive slowly and check speed and RPM needles, coolant needle, digital speed/gear/fuel, and warning lights. The LCD can switch pages by clicking it. The lighting, indicator/hazard, wiper and high-beam controls use their existing dashboard meshes. Neutral only responds below 1 km/h. Select forward/reverse with your normal AC gear controls.
5. Check E200 pedal/parking-brake motion and E6M's final axle wheel rotation. Test forward and reverse. AC still has two physical axles; the E6M third axle is a visual animation.

## What is verified

Both KN5 files, data references, native wheel/instrument/mirror bindings, and copied file hashes pass validation. Offline Blender renders check camera placement/framing. Lua tests exercise telemetry, warning lamps, clickable controls, wipers, and chase positions using mocked CSP APIs. These checks do not verify live AC rendering or handling. The game has not been launched for this update.

OMSI ticketing, passengers, doors, route-keypad operation and the full electrical/air systems are not ported. Exterior lighting is not a complete OMSI light-system conversion; night driving needs further work. This remains a local playable prototype, not a full OMSI simulation.

## Backups and settings

Each bus package has `installation_report.json` with its installed file hashes and backup path. Shared settings backups are under `outputs/shared_settings_backups/`. The installed `kmb_bus_base` chase script changes distances only for these two bus IDs and retains CSP base behavior for other cars. Real Mirrors is a shared CSP setting. The look-back setting is `neck.ini`, `[LOOK] ORIGINAL_LOOK_BACK=1`.

Each `preview/ac_views/` directory contains rendered views, a contact sheet and the camera report. A cockpit look-back render showing the seat is a geometry diagnostic: AC's normal look-back hides the car at runtime.

## Missing-parts repair

The E200's registration is PU 4458 / fleet AAU1, selected from the first entry of the source `REG_AAU.org`. The plate and fleet marking use the original OMSI font bitmap glyphs. The original window alpha replaces the overly transparent converted textures.

Both models now use the working AC bus hierarchy `HUB > WHEEL + SUSP`; the repair preserves every existing mesh's world position. CSP's user `car_instruments.ini` had `[BASIC] ENABLED=0`, preventing cockpit scripts and E6M tag-wheel animation from running. The installation enables that module with a backup, preserving the other instrument preferences. Reload AC for it to take effect. Lua tests check both tag wheels forward, stopped, and reversed; an AC test is still required.
