# Whole Hong Kong — source master and regional production

The user confirmed on November 23, 2026 that the scope includes all Hong Kong
and the driving-test centres/routes in the repository README. Kam Tin remains
the detailed production sample. The source master covers the retained Hong Kong
road inventory; it is not a finished playable whole-territory map.

## Local authoring inputs

`gis/hong_kong_master/` contains the master in **EPSG:2326, metres**:

| File | Purpose |
| --- | --- |
| `hk_roads_grid.json` | Motor-road candidates with OSM way IDs, tags, node references, access review, width provenance and grade-review flags |
| `hk_boundary_grid.json` | Assembled retained Hong Kong administrative boundary, used to clip the inventory |
| `hk_buildings_grid.json` | Simple closed OSM building footprints throughout the boundary; complex building relations remain deferred |
| `hk_terrain_5m.npz` | Full retained 5 m terrain raster, with native coordinates, cell-centre metadata and original NoData values |
| `regions.json` | Six-kilometre production cores, local origins, road quantities and associated approximate exam-centre locations |
| `exam_route_name_candidates.json` | Audit of all 13 README centres and 31 text route records; candidate street-name matches and unresolved steps |
| `hong_kong_master_overview.png` | Source-coverage overview, with public-road candidates, restricted/review roads and approximate legacy exam locations |

`reports/hong_kong_master_readiness.json` records the actual generated counts,
source hashes, regional scope, official tile-index results and limitations.
The retained OSM and terrain snapshots are reused unchanged; this is not a claim
of a new survey or guaranteed completeness.

The November 23 master has **78,674 road parts**, **118,987 simple building
footprints**, and **61 regional cores**. It distinguishes approximately
4,948 km of public-road candidate lines, 691 km of uncertain/review lines, and
1,254 km of restricted/access-review lines. These are mapped line lengths;
divided carriageways count separately. They are not official network mileage.

Run `scripts/prepare_regional_sources.py` after the master build to produce
`gis/hong_kong_master/regions/<region_id>/` road/context extracts, intact building
footprints, native terrain crops, road-review tables and stable boundary-portal
IDs. Source-generated boundary points have null OSM node references; they must
not be treated as surveyed junctions. The small result report is
`reports/regional_source_preparation.json`.

`scripts/verify_hong_kong_master.py` independently checks the generated regional
files against the master. The November 23 pass checked 61 regions, 94,162 context
road records and 140,482 intact context building records (context overlaps count
more than once), plus 1,663 unique boundary-portal identities. Native terrain
pixel alignment/values, source node references and file hashes passed. This
source check does not validate a game mesh, collision or driving experience.

`source/hong_kong_master/road_tile_acquisition_queue.json` lists official LiDAR,
iB1000, orthophoto and alternative 3D-model sheets within 160 m of mapped road
parts. It distinguishes missing downloads from locally retained archives whose
size matches a previous manifest. This size check is not a fresh integrity
verification. Collection/preparation must verify SHA256 and ZIP CRC before using
the archives. Provider-key parameters are omitted from published URLs.

The whole-territory tile index is collected; the detailed tile archives are
acquired in bounded batches. A sheet in the queue is not evidence that its
model, textures or road elevations have been inspected or built.

## All driving-test centres

All 13 centres and 31 route descriptions remain part of the work. Several route
descriptions contain only an area name, roundabout or manoeuvre, rather than a
complete connected street itinerary. Existing `verified` labels in the older
catalogue refer to that catalogue's status; they do not certify a connected
game route, current official itinerary or correct lane movements.

The old **Wing Hau Street / 永孝街** entry conflicts with retained OSM: the
street is in Kwai Chung, whereas the legacy centre coordinates and route text
place it in Kowloon/To Kwa Wan. It requires a source correction before modelling.
Other legacy centre points are approximate and need gate/start-position review.
The audit preserves these uncertainties instead of silently generating a route.

## Rebuild the master

From the repository root, with the existing NumPy, Pillow, Shapely and osmium
dependencies available:

```powershell
python -m pip install --target projects/hk01_kam_tin/source/python_deps pyproj
python projects/hk01_kam_tin/scripts/prepare_hong_kong_master.py
python projects/hk01_kam_tin/scripts/prepare_regional_sources.py
python projects/hk01_kam_tin/scripts/verify_hong_kong_master.py
```

The script reuses cached official indexes. Use `--refresh-index` only to
deliberately replace those snapshots. It rebuilds the ignored master GIS
outputs and its small readiness report; preserve hand edits separately.

## Older local download audit

`scripts/audit_legacy_map_archives.py` catalogues the older repository-root
`all_3324_zips/` and `raw_zips/` folders without extracting or deleting them.
The November 23 audit found 1,456 files: **1,358 invalid ZIPs** (1,294 HTML
responses and 64 other/truncated files), **72 CRC passes**, and **26 ZIPs with
central directories checked but full CRC still pending**. The full CRC pass
used a 3 GiB compressed-input budget. Invalid files are not build inputs.
Archive names alone do not prove that usable territory-wide scenery was acquired.

See `reports/legacy_archive_audit.json` and the ignored per-file inventory at
`source/hong_kong_master/legacy_archive_inventory.json`. Even a CRC pass still
requires dataset/provenance matching and geometry inspection before reuse.

## Detailed Kam Tin loop inputs

The full test-loop envelope is **E824728–825733, N831420–833203**, derived from
the retained source polyline with 160 m context. It covers all eight test
checkpoints, extending the earlier checkpoint 1–2 pilot input set. The original
OSM source polyline is about 3.468 km; the existing filleted game loop is about
3.445 km. Source alignment checks do not validate that game's collision mesh.

Collection includes 12 sheets per LiDAR/iB1000/model dataset, two orthophoto
sheets (T6-NE-A and T6-NE-C), building attributes and the official territory-wide
road-network database. See `reports/full_loop_data_acquisition.json` and
`reports/full_loop_source_readiness.json` for exact hashes and readiness.
Native 0.5 m terrain, 0.25 m orthophoto mosaic, road/spot-height/pedestrian/utility
vectors, building footprints and review queues are under
`gis/high_quality_full_loop/`.

```powershell
python projects/hk01_kam_tin/scripts/collect_build_data.py --scope full-loop
python projects/hk01_kam_tin/scripts/prepare_collected_data.py --scope full-loop
python projects/hk01_kam_tin/scripts/test_full_loop_data.py
```

The acquisition preserves earlier source archives and reuses matching large
models when available. Original pilot commands and output folders remain
separate. Each collection run defaults to a 3 GiB network limit and a 1.5 GiB
per-file limit; directory scope and tile-count guards prevent accidental
whole-territory bulk downloads through the pilot collector.

## Game production

Build separate selectable 1:1 regions from the shared source master. Six-kilometre
cores are production units, not proof of game streaming, a seamless world or
acceptable memory use. Shared roads at boundaries need coordinated endpoints,
profiles and matching source IDs before neighbouring tracks are exported.

Each region still needs reviewed road edges and widths, joined junctions,
bridge/tunnel profiles, clean driving collision, foreground facades, roofs,
kerbs, drainage, signs, lighting, vegetation and LODs. The Route Twisk reference
quality gate in `HIGH_QUALITY_BUILD_PLAN.md` still applies. Do not use a draped
road inventory or an unreviewed photo mesh as a finished collision surface.

Large data, models, images and generated scenes remain local/ignored. GitHub
contains the scripts, documentation and small reports. No game launch or new
track installation is performed by these source-preparation commands.
