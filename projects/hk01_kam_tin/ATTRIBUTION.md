# Sources and attribution

## OpenStreetMap

**© OpenStreetMap contributors.** Road geometry, names, tags, building footprints and boundary geometry originate from OpenStreetMap.

- Copyright/licence: https://www.openstreetmap.org/copyright
- ODbL 1.0: https://opendatacommons.org/licenses/odbl/1-0/
- Regional download provider: Geofabrik, https://download.geofabrik.de/asia/china/hong-kong.html
- Download: https://download.geofabrik.de/asia/china/hong-kong-latest.osm.pbf
- Complete boundary source: https://api.openstreetmap.org/api/0.6/relation/913110/full

The original OSM snapshots and derived GIS inventory are retained with this project. Preserve attribution and assess ODbL requirements for the actual release and derivative database before distributing the finished mod. Inclusion in OSM does not verify present-day motor access, completeness, surveyed dimensions or permission to use unrelated third-party photographs/textures.

## Terrain

**Terrain source: Lands Department, HKSAR Government.**

- Product metadata: https://www.landsd.gov.hk/en/spatial-data/open-data/kf_dtm.html
- Dataset listing: https://data.gov.hk/en-data/dataset/hk-landsd-openmap-5m-grid-dtm
- File: https://www.landsd.gov.hk/landsd_psi_data/SMO/data/Whole_HK_DTM_5m.zip
- DATA.GOV.HK terms: https://data.gov.hk/en/terms-and-conditions

The published metadata describes a 5 m × 5 m grid in Hong Kong 1980 Grid / Hong Kong Principal Datum, stated accuracy ±5 m at 90% confidence. It identifies aerial photography from January/February 2014 and January 2015, publication in 2017, and metadata revision in March 2019. The downloaded archive's HTTP modification date does not establish a newer survey.

Review the applicable government data terms for the intended distribution. Attribution here is a source record, not a complete legal clearance for a future release.

## Newly generated content

The scripts, project organisation, review classifications and previews were created for this new project. Road widths and many building heights are estimates explicitly labelled in the data and Blender object properties. No Google Maps/Street View textures, paid map assets, or geometry from the previous Route Twisk project have been imported.

## CSDI real scenery sample — 6-NE-12D

**Map from Lands Department. Source data © Government of the Hong Kong Special Administrative Region.**

This sample uses the Lands Department **3D Visualisation Map (Individualised models)**, CSDI identifier `landsd_rcd_1671676915450_88604`. The Government and relevant source organisations retain their intellectual property rights in the data. This adapted simulator scenery is independently prepared and is not endorsed by the Government.

- Source website: https://3d.map.gov.hk/
- Dataset: https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671676915450_88604
- Public metadata: https://portal.csdi.gov.hk/geoportal/rest/metadata/item/landsd_rcd_1671676915450_88604
- Download documentation: https://3d.map.gov.hk/mapviewer/app/download-api?l=en-US
- Terms: English **Terms and Conditions of Use** on the source website; a retrieved snapshot is retained in `source/csdi_individualised/TERMS_SNAPSHOT_2026-11-13.txt`.
- Source sheet: `6-NE-12D`, EPSG:2326 bounds E824750–825500, N832400–833000 (750 × 600 m).
- Retrieved: November 13, 2026. Index revision: July 17, 2026 in Hong Kong local time. This is a revision field, not a claim about every object's capture date.
- Original GLTF ZIP SHA256: `c31199b9482748a4dda11698bd636bf201318e87e9c301abb4360911749d3c5b`.
- Official logo source, reproduced only for attribution: https://www.landsd.gov.hk/images/landsd_logo_fb.jpg

The adapted assets use local metre coordinates, resized textures (maximum 2048 pixels), reduced tile-mesh detail, conservative route-corridor cropping, and a visual terrain blend at the temporary road and tile edges. The original download is retained unchanged. One missing building texture in the source ZIP is recorded in the preparation manifest and uses a neutral fallback. Visual scenery is separate from the test road's collision geometry.

The website's use conditions permit browsing, downloading, distribution and reproduction for commercial and non-commercial purposes subject to its conditions, including clear source identification, ownership acknowledgement and the published indemnity and disclaimer provisions. The Download API page additionally requests the Lands Department logo and copyright notice on the map. Those credits appear on the test-start information board, in UI material, and in this file. Preserve this attribution and the applicable terms with copies. Data are supplied as-is without a source-provider warranty of accuracy or fitness.

## Historical OMSI project reference

The user identified `C:/Users/Table/Documents/GitHub/omsi2-hk-1to1` as another local source. Its OSM source snapshots and manifests were inspected read-only. No OMSI map, spline, vehicle or scenery assets have been converted into this Assetto Corsa sample. See `gis/legacy_omsi_reference/inspection.json`. Existing edits in that repository were preserved.

## Full-loop CSDI scenery — version 0.3

**Map from Lands Department. Source data © Government of the Hong Kong Special Administrative Region.**

The complete 3.445 km test loop uses eight sheets from the same Individualised models dataset listed above, retrieved November 13, 2026. Each source sheet is 750 × 600 m in EPSG:2326. Index revisions below are metadata dates, not capture dates for every object. Original archives remain unchanged locally.

| Sheet | Index revision (Hong Kong date) | Original GLTF ZIP SHA256 |
|---|---|---|
| 6-NE-12B | 2024-10-15 | `9df7cb64db6051461db39d97b7809642e17badfc0b2cdc22ff2c486282d1c3b5` |
| 6-NE-12D | 2026-07-17 | `c31199b9482748a4dda11698bd636bf201318e87e9c301abb4360911749d3c5b` |
| 6-NE-17B | 2024-10-15 | `8b57b7d1d3764a372e7b48835a184c7bd6c4b1b45bf22bc0bb16234ae6ab1956` |
| 6-NE-17D | 2024-10-15 | `1475d820bdfbf51af6b0bf1f12f8b579a1259c5b7f41b1a9f180d2fb7bbf607a` |
| 6-NE-18A | 2024-10-15 | `b8fd75d94eab0acbe54c59dd14c57df2002767d335e84f4a42275dffff4e8642` |
| 6-NE-12C | 2024-10-15 | `063016143ebb57c37303ef58e978dcd05b9a776eb5af72e71600a7a4757135cd` |
| 6-NE-13C | 2024-10-15 | `cd8ab9fe2695c2f75b2a79821db0a5278cba81ceb1b553baf779d667ca05131c` |
| 6-NE-18C | 2024-10-15 | `cafb16abf3f99d10684e05d474b1d0bf199f2a2d07bc1aef9abd67755e277d85` |

Adaptations: local metre coordinates; scenery selection approximately 190 m from the loop; an 11 m protected road corridor; duplicate-building ownership by source sheet; spatial batches; distance-based mesh reduction; DDS BC1 textures with complete mip chains, capped at 2048 pixels (distant buildings at 1024); and visual terrain blending toward the temporary road and outer source boundary. Missing source textures use neutral fallbacks. Invalid source UV pairs in three infrastructure batches were repaired from the nearest valid UV in the same batch; original archives are unchanged. Repairs and fallbacks are recorded in the preparation reports. Scenery is visual-only. Original road, pit, barrier collision and spawn/timing nodes are retained.

The logo and source/ownership notice appear on the start board and UI preview. Preserve these credits and the retained terms with the package. Source data are supplied as-is; this simulator adaptation is independently prepared and is not endorsed by the Government.
