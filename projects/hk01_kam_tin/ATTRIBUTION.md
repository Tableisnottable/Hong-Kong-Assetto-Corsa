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
