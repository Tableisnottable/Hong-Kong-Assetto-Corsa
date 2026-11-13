# Hong Kong 1:1 — new regional Assetto Corsa project

**Current deliverable: driving-test version 0.2 with a real CSDI scenery sample.** The current package is `release_csdi_sample/content/tracks/hk01_kam_tin_test`, displayed as **Hong Kong — Kam Tin Driving Test**. It is a 3.445 km solo loop. Real Lands Department scenery covers one 750 × 600 m tile, `6-NE-12D`; other areas remain blockout. Use **Practice, one car, clear daytime, start from pits**. File, texture and geometry checks passed; actual game loading, driving and FPS remain pending the user.

The rest of the 6 × 6 km region remains a geographic blockout. Open `blender/HK01_KamTin_CSDI_SAMPLE.blend` to edit the scenery sample. The version 0.1 driving scene and original foundation remain separate. See `driving_test/csdi_sample/reports/package_verification.json` for current package/install results. The CSDI scene retains all 272 physical mesh payloads and all spawn/timing matrices from version 0.1. Textures are capped at 2048 pixels; tile meshes are reduced and cropped away from the road. Terrain transitions, rough photogrammetry and one missing source texture remain test-build limitations.

The source download was 312.6 MB; the version 0.2 KN5 is about 504 MB and its install ZIP about 450 MB. These large local assets are excluded from GitHub. GitHub contains code, documentation, small track configuration/source-selection files and validation summaries only. A Git clone alone is not the installed playable package.

This project starts from new geographic source data. It does not reuse or modify the existing Route Twisk geometry.

## Open the first region

Open `blender/HK01_KamTin_ShekKong_FOUNDATION.blend` in Blender 5.1 or later. The selected region is **6 × 6 km around Kam Tin and Shek Kong**. The overview image is in `previews/`. The Blender file includes a `READ_ME_FIRST.txt` text block, named collections, source IDs, and quality flags.

The complete downloaded Hong Kong road inventory is retained in `gis/hk_roads.geojson` and `gis/hk_roads_grid.json`. This is the basis for expanding to further regions, not a claim that every real road has already been captured or modelled.

## What exists

- A Hong Kong-wide inventory of candidate motor roads, clipped to the separately assembled Hong Kong administrative boundary.
- Road names, source tags, source node IDs, access categories, and estimated/tagged widths. Clip-generated points have null node IDs; they must not be treated as surveyed junctions.
- Separate public-road candidates, restricted/access-review roads, and uncertain tracks or conditional access.
- A local 1:1 regional Blender scene with terrain, terrain-draped road reference strips, and simple building masses.
- A retained 5 m terrain crop, a 100 m whole-territory terrain overview, and a lighter 20 m regional terrain mesh.
- A 1 km authoring grid, a road review queue, source checksums, and reproducible scripts.

## What does not exist yet

For the full region there is no final road surface, stitched junction network, verified bridge/tunnel elevation, surveyed lane width, detailed building façade, finished roadside scenery, driving AI, or traffic system. The separately exported test loop has simplified drivable surfaces and spawn/pit nodes. No gameplay or frame-rate result is claimed.

Road reference strips overlap at junctions and are not collision geometry. Grade-separated roads are deliberately marked **violet** and draped on the terrain for identification; their current displayed height is not their real bridge/tunnel height. **Amber** marks roads requiring access or road-type review. Grey buildings are massing placeholders, generally with estimated heights. Complex building relations are deferred.

## Coordinates and scale

- Master horizontal reference: **Hong Kong 1980 Grid, EPSG:2326**, in metres.
- Blender regional origin: **E 826000 m, N 833000 m**.
- Blender X = east, Y = north, Z = up; **one Blender unit = one metre**.
- Local X = master easting − 826000; local Y = master northing − 833000.
- Terrain heights use Hong Kong Principal Datum. They are not survey-accurate road deck profiles.
- Foundation `.geojson` files use WGS84 longitude/latitude; `*_grid.json` uses EPSG:2326. The explicitly labelled historical stop reference, if populated, also uses EPSG:2326. Check each file's CRS instead of inferring it from the extension.
- Assetto Corsa export is Blender `(x, z, -y)`. AC local +Z is vehicle travel forward. Small orientation and spawn-support checks were completed; raw map-grid coordinates are not passed into the game.

## Regional release approach

The delivery plan is **separate selectable regional tracks at real scale**, built from shared master geographic data. There is no assumed seamless travel between tracks and no assumed whole-city streaming system. A 1 km authoring tile is an editing/export organisation unit, not proof that the game streams that tile.

Start with HK01. Build and validate a short connected public-road loop first; then extend to the rest of the region. Expand outward toward Yuen Long, Route Twisk/Tsuen Wan, and the wider New Territories once the first region meets the quality and performance gates. Dense urban Kowloon, Hong Kong Island, major interchanges and harbour crossings need their own production passes.

## Hardware target

Detected on November 13, 2026: RTX 4060 Laptop GPU, 8188 MiB VRAM, Core i7-13800H, about 63.6 GiB usable system RAM. Aim for high detail near the road, with simpler distant buildings and vegetation. **60 FPS is a provisional design target, not a measured result.** Resolution, CSP options, weather, traffic and car count remain to be selected/tested.

The next performance experiment should use a representative finished kilometre of road, not this lightweight geographic blockout. Measure frame times, VRAM use, draw calls, load time and physics behaviour before setting regional asset budgets.

## Next production gates

1. **Road truth:** compare the regional road inventory with authoritative road data and reference imagery that permits the intended use. Resolve restricted roads, missing links, conditional access and boundary exits.
2. **Playable greybox:** choose a short connected public-road loop. Set real widths and profiles, construct junction surfaces, resolve every bridge/tunnel on the loop, then produce separate visual and collision meshes. Add safe boundaries and spawn/pit objects.
3. **Export validation:** perform a small KN5/material/axis test with the installed Assetto Corsa SDK. Only then export the loop. Do not install this foundation as if it were finished track content.
4. **High-detail sample:** finish one representative kilometre of lane markings, drainage, kerbs, barriers, signs, lighting and local buildings. Use reusable Hong Kong roadside assets, measured dimensions and source records.
5. **Regional completion:** extend the validated process to the whole HK01 network. Review every seam, junction, grade transition and collision edge. Add optional traffic separately after the driving surface is stable.
6. **Benchmark and release:** test the actual final geometry on the target PC and record settings/results. Review source licences and attribution before distributing a release. Subsequent regions reuse the same pipeline and asset library.

## Rebuild

Install Python dependencies into a project-specific environment using `scripts/requirements.txt` (built here with Python 3.12). The scripts also recognise this task's `work/python_deps` folder when it exists.

```powershell
python scripts/prepare_geodata.py
python scripts/validate_and_preview.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python scripts/build_blender.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup blender/HK01_KamTin_ShekKong_FOUNDATION.blend --python scripts/verify_blender.py
```

`prepare_geodata.py` reads the retained source snapshots in `source/`. It does not fetch changing data during a rebuild. Rebuilding will replace generated GIS, report, preview and Blender outputs in this project; save any manual scene edits in a different file first.

## Source accuracy and rights

Read `ATTRIBUTION.md` and `reports/source_manifest.json`. The terrain metadata states a 5 m grid and ±5 m accuracy at 90% confidence, based on photography from 2014–2015. Recent roadworks, retaining walls, road camber, kerbs, bridge decks and tunnel interiors need additional modelling. A 1:1 scale model is not automatically a survey-accurate reconstruction.

The road and terrain snapshots are retained for reproducibility. Their timestamps are separate: the OSM extract timestamp is in `reports/data_inventory.json`; the separately fetched boundary may be newer. Source-file modification dates must not be interpreted as new terrain survey dates.

## CSDI sample build

The source terms and attribution are recorded in `ATTRIBUTION.md`. Download only the tile being tested; do not bulk-fetch Hong Kong without a region budget. `fetch_sources.py` resolves the public government's download index at run time and does not place API keys in source code.

```powershell
python -m pip install -r scripts/requirements.txt
python scripts/fetch_sources.py --foundation --sheet 6-NE-12D
python scripts/prepare_geodata.py
python scripts/prepare_driving_test.py
# Build the v0.1 baseline scene/KN5 first (large, local outputs):
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python scripts/build_driving_test.py
python scripts/prepare_csdi_scenery.py
python scripts/prepare_csdi_ground.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python scripts/build_csdi_sample.py
```

Packaging is deliberately gated by hash-bound independent binary/scenery validation reports. `package_csdi_sample.py` refuses stale or failed reports and preserves a modified installed track. The retained reports document this build; they must be regenerated after changing geometry. The native SDK graphics check did not initialise on this machine, so it is not evidence of engine acceptance.

For the small GitHub source tree, see `PUBLISHING.md` and `validation_summary.json`. The historical OMSI repository was inspected read-only and contains reference data rather than a finished high-detail scene for this test loop.
