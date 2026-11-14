# A practical route to a high-quality Hong Kong map

Research checked on November 14, 2026. The visual target is the user's installed
Route Twisk RWE / Repack Test. This document defines a production method; it does
not approve the current Kam Tin build as meeting that target.

Build a geographically accurate base from government data, then author the road
and objects seen from the driver's seat. Use separate 1:1 regional tracks with a
shared asset library. Prove the result on the 431 m section between Kam Tin test
points 1 and 2 before applying the method to the remaining 3.445 km loop.

## Why the current approach falls short

The existing road uses a temporary seven-metre strip and simplified junctions.
Aerial photo meshes can contain blurred walls, tangled vegetation and terrain
fragments. Earlier cleanup projects GENERIC geometry onto terrain; that is unsafe
as a general production rule because GENERIC can also contain structures. The
later building-preservation repair is useful, but does not create detailed
facades or verify the remaining shapes.

The reference audit found ordinary `ksPerPixel` and `ksPerPixelAT` materials on
many inspected assets. More complex shaders or larger textures alone will not
close this gap. Road shape, coherent building silhouettes, materials at the
correct scale, local roadside detail and vegetation placement all matter.

## Sources now verified

The bounded pilot envelope is E825184–825535, N832215–832871 in EPSG:2326.
It is an acquisition envelope around the checkpoint section, not a surveyed road
boundary. Counts below refer to that rectangle or the explicitly named tile.
The machine-readable evidence is in `reports/high_quality_source_research.json`.

| Source | Verified evidence | Production use and limit |
|---|---|---|
| [LandsD Building](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637211194312_35158) | 418 intersecting records; 127 have numeric base/top heights with a positive difference; 291 have missing or invalid pairs | Building footprints and source identities. Compute height as top minus base; incomplete records require another source or explicit review. |
| [CEDD LiDAR](https://portal.csdi.gov.hk/geoportal/?datasetId=cedd_rcd_1629267205233_87895) | Four DTM_2020 tiles intersect. Downloaded 6NE12D is a 1500 × 1200 GeoTIFF with 0.5 m pixel spacing. | Ground shape and terrain fitting. Acquisition was December 2019–February 2020; pixel spacing does not establish vertical accuracy or current road levels. |
| [LandsD iB1000](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637223748322_25497) | Downloaded 6-NE-12D GML contains 558 Building features, 68 StreetCentreLines, 219 CartoTransLine, 163 SpotHeight and 252 UtilityPoint features. | Detailed placement and profile references. Building GML includes BASELEVEL/ROOFLEVEL. Decode line/point classification from the official dictionary before treating it as a road edge, lamp or other object. |
| [True Digital Orthophoto](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1701762716904_4826) | Published resolution 0.25 m; pilot index points to T6-NE-C, with photograph date January 3, 2025. Index checked; raster not downloaded in this research. | Check junction outlines, ground use and object placement. It cannot supply clear vertical facades, kerb heights or hidden ground. |
| [3D non-textured models](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1742809441342_98380) | Four intersecting download-index sheets; metadata and format fields checked. Actual model geometry not downloaded or inspected here. | Candidate cleaner building/infrastructure geometry to inspect and texture. Do not assume watertight or driving-ready meshes from the index alone. |
| [3D Spatial Data 3D-BIT00](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1637306559892_42396) | Four intersecting index sheets. Metadata describes footprint-extruded Level 1 buildings, selected textured landmark models, infrastructure and terrain. | Alternative geometry where the photo mesh is damaged. Detailed landmark coverage is selective; the pilot models remain to be inspected. |
| [3D individualised models](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671676915450_88604) | Eight source sheets already used by this project | Retain good buildings and background scenery; replace poor foreground objects individually. Do not flatten an entire unclassified category or delete a whole building to clear a provisional route. |
| [Transport Department road network v2](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2) | Official catalogue describes directions, junction turning restrictions, stopping restrictions and parking | Check road connectivity and restrictions before a later traffic pass. This research did not download or validate its local geometry. |

Two actual sample ZIPs, approximately 10.7 MB combined, passed CRC checks. Source
responses and downloads stay in ignored `source/quality_research/`. The published
report omits provider download keys. Metadata revision dates are separate from
the capture dates of the features inside a tile.

## How to build the pilot

1. **Establish the real road.** Acquire the four relevant iB1000 tiles and the
   applicable data dictionaries. Cross-check their linework against orthophotos,
   spot heights, LiDAR terrain and permitted street-level references. Produce a
   reviewed road-edge, junction and elevation layout. Record uncertain changes,
   bridge decks and occluded ground rather than draping every road over terrain.
2. **Model the driving surface.** Construct joined junctions, actual width changes,
   camber, shoulders, kerbs and drainage. Build a clean continuous collision mesh
   from the reviewed layout, with a separate detailed visual surface. Place paint
   and repair decals at realistic size; do not bake image shadows into asphalt.
3. **Rebuild nearby buildings.** Match each footprint to its source IDs and inspect
   available individualised, non-textured and BIT00 geometry. Use valid datum
   heights; cross-check the different source dates before choosing among them.
   Author missing roofs, wall volumes, windows, balconies, shopfronts and rooftop
   equipment where visible. An extruded footprint is a useful base, not a finished
   facade. Missing heights stay in a review queue; generic assumed heights must
   remain labelled as estimates. Check base-to-ground contact and intact roofs
   from both driving directions.
4. **Build a reusable Hong Kong roadside library.** Kerbs, gullies, channels,
   railings, W-beam barriers, retaining walls, street lamps, utility poles, traffic
   signs, road lettering and bus stops need consistent measured dimensions.
   Place them from evidence; a safety rail around the whole loop is not a record
   of the real roadside. Make collision match the visible solid objects.
5. **Author vegetation and ground together.** Use varied trees and undergrowth,
   convincing leaf cutouts and species-appropriate silhouettes. Avoid inferred
   tree placement on rooftops or roads. Blend terrain materials around buildings,
   drains and verges; retain aerial imagery mainly for layout and distant ground.
6. **Review at car height, then test.** Render forward, reverse, junction and
   building close-up views before export. Check continuous collision support in
   both lanes, junction seams, walls, spawns and pit returns. The user's Assetto
   Corsa comparison must use the same car, weather/time and graphics settings as
   Route Twisk. Blender renders and binary checks cannot approve game appearance.

For owned or appropriately licensed facade photographs, rectify perspective and
remove baked lighting before making atlases. Photogrammetry of a landmark can
help when suitable source photos exist; it still needs cleanup and game LODs.
Government map terms and attribution remain attached to derived scenery. There
is no assumption of permission to extract textures from another map or imagery
service.

## Detail and performance on the target PC

Use the recorded RTX 4060 Laptop 8 GB / i7-13800H / 64 GB hardware as the initial
target, then confirm through the user's measurements. Aim for 2560 × 1440 at
60 FPS, equivalent to about 16.7 ms per frame. This is a target, not a promise.

- Within roughly 0–60 m of the road: model facades, roofs, kerbs and fixtures with
  clear silhouettes; give visible surfaces appropriate texture density.
- Roughly 60–250 m: use simpler building/vegetation LODs and inspected government
  meshes. Keep recognizable landmarks detailed when they occupy many pixels.
- Beyond roughly 250 m: retain the skyline and terrain with inexpensive meshes,
  lower texture resolution and restrained vegetation. Distances are starting
  settings to tune for sightlines, not hard acceptance thresholds.
- Split scenery into spatial batches of about 50–100 m, group compatible
  materials, provide mipmaps and useful LOD distances, and limit vegetation alpha
  overdraw. Avoid hundreds of unique large facade textures on small distant objects.
- Measure actual frame time, GPU memory, load time and worst-case views with the
  chosen car and CSP settings. Embedded texture bytes and total triangle counts
  cannot predict the result. The track must leave memory for the car, sky, CSP
  effects, render targets and the operating system.

Keep authoritative coordinates in EPSG:2326 and heights in their confirmed datum.
Transform in float64 to a local origin before producing float32 game meshes.
Individual regional tracks can have their own origins while sharing the master
geographic database. Authoring tiles, multiple KN5s and LODs do not by themselves
provide seamless streaming or reduce all startup memory.

## Deliverable before expanding

Finish the 430.6 m checkpoint 1–2 pilot (existing route chainage 150–580.6 m), with
all buildings visible from the road reviewed, one coherent road/roadside material
set, joined junctions and a source-linked asset manifest. Keep the installed test
loop available while this is authored separately. Capture matched car-height
comparisons and a user-driven performance test before extending the process to
the rest of Kam Tin, then neighbouring 1:1 regional tracks. Dense urban streets,
tunnels and major interchanges need further dedicated production passes.

The process can reach a much stronger result than the current conversion, but
high-quality nearby architecture and streetscape still require substantial
asset authoring and visual iteration. No automatic whole-Hong-Kong conversion has
been demonstrated to meet the reference.

## Reproduce the source feasibility check

From the repository root, using Python 3.12 or later (standard library only):

```powershell
python projects/hk01_kam_tin/scripts/research_quality_sources.py --probe-sheet 6-NE-12D
```

Omit `--probe-sheet` for metadata, bounded building features and tile indexes
only. Each sample ZIP is limited to 32 MiB. The script queries all returned object
IDs in batches and refuses incomplete responses, records archive hashes and CRC,
and reads TIFF grid tags/GML feature counts without installing anything. It
collects research evidence; it does not produce a finished track.
