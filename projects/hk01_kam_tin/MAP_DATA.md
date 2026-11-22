# Map build inputs — Kam Tin

For the November 23 extension to the **whole-Hong-Kong source master**, all
README exam centres/routes, and the full Kam Tin loop source set, see
[FULL_HONG_KONG.md](FULL_HONG_KONG.md). The original checkpoint 1–2 pilot inputs
and commands below remain separate from that wider acquisition.

The acquisition follows the README and `HIGH_QUALITY_BUILD_PLAN.md`: first
prepare the checkpoint 1–2 pilot, then extend the same method along the test
loop. Its envelope is E825184–825535, N832215–832871 in Hong Kong 1980 Grid
(EPSG:2326). This is a source-selection rectangle, not a surveyed road boundary.

## Where the data go

Paths below are relative to `projects/hk01_kam_tin/`.

| Input | Local location | Use |
| --- | --- | --- |
| Retained Hong Kong OSM extract and complete boundary | `source/hong-kong-latest.osm.pbf`, `source/hong-kong-boundary-913110.osm` | Road inventory, names, access tags and regional clipping. The retained snapshot is not silently refreshed. |
| Retained whole-Hong-Kong 5 m terrain | `source/Whole_HK_DTM_5m.zip` | Foundation terrain and distant context. |
| Four 0.5 m LiDAR DTM tiles | `source/map_build_20261115/extracted/lidar_dtm_2020_*/` | Native terrain samples around the pilot. Pixel spacing does not establish road-level accuracy. |
| Pilot terrain crop | `gis/high_quality_pilot/pilot_dtm_05m.npz` | Pixel-aligned mosaic of those four tiles, with coordinates and cell size stored in the file. No smoothing or height offset. |
| Four iB1000 GML tiles | `source/map_build_20261115/extracted/ib1000_*/` | Building outlines, street centre lines, topographic linework, spot heights and utility points. Source coordinates are stored N,E in this export and are checked against the official tile boundaries before conversion. |
| iB1000 dictionary and licence | `source/map_build_20261115/extracted/ib1000_GML_resources/` | Read the GML dictionary before interpreting classification codes. The bundle includes `LICENSE.txt`. |
| Building footprints and attributes | `source/map_build_20261115/index/buildings_features.json` | Source IDs, footprints, names and base/top datum heights, in EPSG:2326. |
| Building height review | `gis/high_quality_pilot/building_height_review.csv` | Separates valid top-minus-base heights from records that still require another source. |
| True digital orthophoto T6-NE-C | `source/map_build_20261115/extracted/tdop_T6-NE-C/` | Full official georeferenced TIFF, photographed January 3, 2025, at 0.25 m per pixel. |
| Pilot orthophoto crop | `gis/high_quality_pilot/pilot_orthophoto.jpg` plus `.jgw` world file and `.crs.txt` | 1,404 × 2,624 px crop of the full source for road edges, junctions, verges and building placement. No resampling; JPEG quality 95. |
| Four non-textured 3D model tiles | `source/map_build_20261115/extracted/nontextured_models_*/` | Cleaner glTF building and infrastructure candidates for inspection and later texturing. |
| Four 3D-BIT00 tiles | `source/map_build_20261115/extracted/bit00_*/` | Alternative FBX building/infrastructure geometry; compare with the other sources before choosing models. |
| Existing individualised scenery | Machine-local archive paths in `source/map_build_20261115/local_manifest.json` | Reuses four matching archives from the earlier project without downloading or copying the large scenery again. |
| Territory-wide official road network v2 | `source/map_build_20261115/extracted/td_road_network_v2.gdb/` | Connectivity and road/traffic attributes in the supplied file geodatabase. |
| Road-network specifications | `source/map_build_20261115/extracted/td_road_network_spec/` | Official field definitions; the CSV download list is retained under `references/`. |
| Pilot iB1000 vector extracts | `gis/high_quality_pilot/iB1000_*_pilot_grid.json` | Clipped street centrelines, cartographic transport lines and spot heights, converted to EPSG:2326 east,north coordinates. Heights remain source attributes, not assigned to road meshes. |
| Pilot building vector extract | `gis/high_quality_pilot/LandsD_building_footprints_pilot_grid.json` | Clipped building outlines with IDs, names, base/top fields and an explicit height-review flag. |

The four detailed-map, terrain and model sheets are **6-NE-12D, 6-NE-13C,
6-NE-17B and 6-NE-18A** (LiDAR names omit the hyphens). They cover the pilot
envelope; they do not cover every road in the full 6 × 6 km region. The retained
OSM extract, 5 m terrain and TD road network have wider coverage.

## Reading the map layers safely

The official iB1000 GML dictionary is extracted beside its PDF. Use
`StreetCentreLines.gml` and its `STREETTYPE`/`DISPLAYSTATUS` attributes for
classified street-centreline references. It distinguishes highway, main road,
restricted road, road bridge, secondary road, slip road, track and tunnel.
`CartoTransLine.gml` is cartographic transport linework: its classes include
flyovers/bridges, under-flyover lines, tunnels and road margins. It helps
identify grade separation, but is not itself a drivable road edge or deck-height
surface. Its `TC` class means track in this tile, while `RM` means road margin.
The TD road-network specification describes centreline, turn-restriction and
intersection entities, as well as bus-only lanes, speed limits and vehicle
restrictions. Those attributes support connectivity and access review; verify
the spatial reference and fields in the unpacked geodatabase before joining
them to iB1000 or OSM.
Spot-height points distinguish `SHG` (ground) from `SHE` (top of an elevated
structure); keep them separate when checking LiDAR and road elevations.

For this rectangle, the extracted iB1000 layers contain 34 clipped street
centrelines (all classified SER), 74 cartographic transport lines (69 RM and
5 TC), and 106 ground spot heights. Four hundred eighteen building footprints
intersect the envelope; 127 have usable top/base pairs and 291 need a height
source or manual review. These are pilot-envelope counts, not whole-tile or
regional totals. `map_source_readiness.json` records the full code counts.

`reports/map_data_acquisition.json` records acquisition status, byte counts,
SHA256, original download/reuse methods and archive CRC checks. The original
collection used about 621 MiB of network downloads; the four matching
individualised scenery archives were reused in place.
`reports/map_source_readiness.json` records extracted inputs, GML feature
counts, terrain coverage, decoded feature-code guidance, height completeness,
and the orthophoto crop's alignment.
The ignored `local_manifest.json` also records machine-specific source paths.

## Reproduce or resume

From the repository root:

```powershell
python projects/hk01_kam_tin/scripts/collect_build_data.py
python projects/hk01_kam_tin/scripts/prepare_collected_data.py
```

The collector in this PC reuses its retained OSM/5 m terrain inputs and four
matching large scenery archives. The preparation step rechecks archive CRCs,
creates the pilot LiDAR and orthophoto crops, converts the three iB1000 layers,
and exports clipped building footprints. Preparation takes a few minutes because
it verifies and unpacks the source models; it can be rerun without redownloading.

Collection uses the standard library. Preparation uses the project's existing
NumPy and Pillow dependencies. If an earlier project folder is available, pass
`--reuse-project` followed by its path to the collector to reuse foundation files
and matching individualised scenery archives. Without it, missing originals are
downloaded within a 3 GiB per-run budget and a 1.5 GiB per-file budget. Existing
sources are retained and verified. Use `--refresh-index` only when deliberately
acquiring a new source-index snapshot. To change geographic coverage, review the
bounded selection and tile budget first; this is not a whole-territory bulk
model downloader.

The preparer checks archive hashes and CRC before extraction and refuses to
overwrite an extracted file that has changed. Keep edited model assets in a
separate authoring directory. A failed download is listed in the acquisition
report; rerunning the collector retries missing files. Inspect the report's
status rather than treating the presence of a folder as a complete acquisition.

## Use the inputs for the next build

1. Keep master coordinates in EPSG:2326. For the existing project origin,
   subtract E826000 and N833000 before producing local mesh coordinates. The
   terrain NPZ stores pixel-centre coordinates as well as the outer grid edge;
   do not introduce a half-pixel shift. Preserve native heights until the LiDAR
   datum and its agreement with iB1000 spot heights have been checked.
2. Decode iB1000 linework with its dictionary and compare it with the orthophoto
   and terrain. Review actual road edges, widths, junction shapes, bridge decks
   and occluded ground before creating a driving surface.
3. Match building IDs and footprints across the candidate model datasets.
   Building height is top minus base, not the top datum height alone. Use the
   height review CSV for incomplete records. Inspect geometry before assigning
   foreground detail, textures and LODs.
4. Author roads, facades, kerbs, drains, walls, signs and vegetation where the
   sources are incomplete. Review close to driver height, then build separate
   visual and collision meshes and measure the result in the game.

Acquiring these sources does not modify the installed v0.5 track or satisfy its
Route Twisk quality target. Source capture dates differ; download and index
revision dates are not new survey dates. Street-level facade photographs,
occluded features and current roadworks still need suitable references or
explicit review.

## Source credits

Retain **© OpenStreetMap contributors** and the ODbL information for OSM inputs.
Government building, topographic, terrain, imagery and model data come from the
Lands Department and CEDD; road-network data come from the Transport Department,
HKSAR Government. Keep their metadata and terms with derived work. The iB1000
resource licence and retained DATA.GOV.HK terms are part of the local input set.
See `ATTRIBUTION.md` and the per-file source URLs in the acquisition report.
Large downloaded data and extracted models remain local; only collection code,
documentation and small sanitised summaries are intended for GitHub.
