# Hong Kong 1:1 — regional Assetto Corsa project

**Quality target: the user's installed Route Twisk RWE / Repack Test. Current v0.5 is a comparison build and has not reached that standard.** The target and outstanding production requirements are recorded in `REFERENCE_QUALITY.md`. Geographic scale and static export checks alone do not establish finished game quality.

The [high-quality build plan](HIGH_QUALITY_BUILD_PLAN.md) records the November 14 source research: a verified 0.5 m CEDD LiDAR sample, detailed iB1000 GML, official building footprints/heights, and a 431 m pilot using authored roads and nearby buildings. Its evidence and reusable collector are in `reports/high_quality_source_research.json` and `scripts/research_quality_sources.py`. This research does not change or approve the installed track.

The pilot's map inputs were collected on **November 15, 2026**, including four LiDAR tiles, four iB1000 tiles and their dictionary, orthophoto, building attributes, alternative 3D models and the TD road-network database. Local preparation outputs include a 0.5 m terrain crop, georeferenced orthophoto crop, clipped iB1000 street/grade/spot-height vectors, and building-footprint vectors. See [MAP_DATA.md](MAP_DATA.md) for locations and reproducible commands, and `reports/map_data_acquisition.json` for file hashes and acquisition results. Large source assets stay local. This is source preparation, not a new installed track build.

Version 0.5 is installed as **Hong Kong — Kam Tin Driving Test**, a provisional 3.445 km loop. Use **Practice, one car, clear daytime, start from pits**; restart the session, keep previous graphics/time/weather and follow the eight blue markers. See `TESTING.md` and `STATUS.md`.

This pass adds photographed asphalt and generic fallback ground, worn alpha-cut paint, a new cutout foliage atlas with eight tree shapes, photographed bark, smoothed visual terrain and authored steel safety rails/posts/bolts/reflectors. It preserves original collision payloads and spawns. Rails follow test safety bounds; coarse wall collision remains behind them. Accurate road/junction/kerb/drainage/roadside production, varied local vegetation and source-ground/facade cleanup are unfinished. Reference map assets are not copied and the reference installation is unchanged.

Binary/images, alpha-cut materials, protected road/pit clearance, baseline payload/spawns, archive CRC and installed hashes passed. Blender views were inspected, but **v0.5 engine appearance, driving and FPS await the user**. It is not all Hong Kong, and no AI traffic, rain/night or multiplayer validation is included.

Local stage: `release_finish_v05/content/tracks/hk01_kam_tin_test`. Editable scene: `blender/HK01_KamTin_FINISH_v05.blend`. 11 models contain 7,836,878 triangles (2,061.8 MB KN5; 1,023.0 MiB embedded texture payload). Large assets stay local; GitHub has small sources/configuration/docs/reports only. Cloning it alone does not install the track.

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

For the full region there is no final road surface, stitched junction network, verified bridge/tunnel elevation, surveyed lane width, detailed building façade, finished roadside scenery, driving AI, or traffic system. The separately exported test loop has simplified drivable surfaces and spawn/pit nodes. The user loaded/drove v0.3; no complete-lap benchmark or v0.4 engine result is claimed.

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

Detected on November 13, 2026: RTX 4060 Laptop GPU, 8188 MiB VRAM, Core i7-13800H, about 63.6 GiB usable system RAM. Aim for high detail near the road, with simpler distant buildings and vegetation. **60 FPS is a provisional design target, not a measured result.** The user tested v0.3 at 2560 × 1440; a complete-lap benchmark and v0.4 test are still required.

Benchmark the installed full-loop test and record resolution, car, graphics/CSP settings, frame times, VRAM, load time and physics behaviour. The file-based texture budget does not establish real game performance. Use the results before expanding the region.

## Regional production gates

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

## Earlier one-tile sample build

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

## Full-loop 0.3 rebuild

Build the foundation and version 0.1 loop first using the commands above. Preserve any hand edits separately before regenerating output. Then run:

```powershell
python scripts/fetch_route_scenery.py
python scripts/prepare_route_scenery.py --finalise
python scripts/prepare_route_ground.py
python scripts/verify_route_textures.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python scripts/build_csdi_sample.py -- --full-route
python scripts/verify_track.py release_route_scenery/content/tracks/hk01_kam_tin_test/hk01_kam_tin_test.kn5 --baseline release/content/tracks/hk01_kam_tin_test/hk01_kam_tin_test.kn5 --models-ini release_route_scenery/content/tracks/hk01_kam_tin_test/models.ini --report driving_test/route_scenery/reports/package_model_verification.json
python scripts/package_route_scenery.py
```

The downloader selects only sheets intersecting the loop's 160 m buffer and records sanitized checksums. The preparation uses a 190 m detail radius, removes source geometry from an 11 m road corridor, and budgets texture memory before export. The packager requires passing reports tied to current KN5 hashes. Add `--install-root` with the Assetto Corsa installation folder only when intentionally installing this test track; modified installed files are preserved by a refusal to overwrite them.

## Visual repair 0.4 rebuild

Retain the completed v0.3 source scene and package as inputs. Do not run the older packager over a v0.4 installation. Then run:

```powershell
python scripts/prepare_quality_pass.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python scripts/build_quality_pass.py
python scripts/verify_track.py release_quality_v04/content/tracks/hk01_kam_tin_test/hk01_kam_tin_test.kn5 --baseline release/content/tracks/hk01_kam_tin_test/hk01_kam_tin_test.kn5 --models-ini release_quality_v04/content/tracks/hk01_kam_tin_test/models.ini --report driving_test/quality_pass/reports/model_verification.json
python scripts/review_quality_pass.py
# Inspect all eight current renders. Only after inspection, record specific notes:
python scripts/review_quality_pass.py --record-inspection --notes "Describe the observed geometry and remaining defects here."
python scripts/package_quality_pass.py
```

`--record-inspection` records a deliberate reviewer action; it is not automatic visual approval. `package_quality_pass.py` requires passing hash-bound model checks, explicit zero-emissive materials, current render/review hashes, preserved physics/spawns and the unchanged owned v0.3 input package. With an intentionally supplied `--install-root`, it refuses to overwrite user additions or modified installed files. Global graphics/CSP settings are not changed. Version 0.3 remains a separate local rollback.

## Reference-informed 0.5 rebuild

Keep the completed v0.4 Blender scene and owned package as separate inputs. Do not run an older packager over a newer installation.

```powershell
python scripts/fetch_finish_assets.py
python scripts/prepare_finish_pass.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python scripts/build_finish_pass.py
python scripts/verify_track.py release_finish_v05/content/tracks/hk01_kam_tin_test/hk01_kam_tin_test.kn5 --baseline release/content/tracks/hk01_kam_tin_test/hk01_kam_tin_test.kn5 --models-ini release_finish_v05/content/tracks/hk01_kam_tin_test/models.ini --report driving_test/finish_pass/reports/model_verification.json
python scripts/review_quality_pass.py --pass-id finish_pass
# Inspect all eight current images before deliberately recording observations:
python scripts/review_quality_pass.py --pass-id finish_pass --record-inspection --notes "Record observed geometry defects and limitations here."
python scripts/package_finish_pass.py
```

The packager additionally requires a current independent base-model report at `driving_test/finish_pass/reports/base_independent_verification.json`; the local read-only standalone parser check used here is identified in the retained summary and is not distributed. An intentionally supplied `--install-root` installs only an unchanged owned track and refuses user additions/modified files. The official external texture checksums are pinned in `sources/finish_assets.json`; the completed v0.4 source scene is also required. Old releases remain separate. This authoring pipeline does not automatically approve matching the quality reference.
