# Kam Tin building-shape authoring review

The November 23 pass builds a separate scene for the approved checkpoint 1–2
pilot. The whole-Hong-Kong scope remains in `FULL_HONG_KONG.md`; this scene is
the detailed sample used to evaluate the building pipeline before wider use.

Open the local `blender/HK01_KamTin_BUILDING_REVIEW.blend` in Blender 5.1.
It opens with clean building candidates and footprint outlines. All source
geometry is at the established E826000/N833000 origin, in metres. Source
positions and native heights are retained. The installation is unchanged.

## What is prepared

- 147 official building footprints lie within 60 m of the pilot reference line.
- 37 footprint records have matched individual building candidates: 37 clean
  non-textured variants and 37 textured variants, linked through GeoRefNo.
- The clean importer accepts `COLOR_0` vertex colours without requiring
  `TEXCOORD_0`. The older photo importer assumes UVs, so it could not read these
  clean models directly.
- Candidate flags identify 14 model variants with convex-hull overlap below
  50%, eight with height differences over 2 m, and one missing source texture.
  Flags can overlap on a model. These are review flags, not automatic repairs.
- 110 nearby footprints lack an individually matched source model in this set.
  Of those, only three have usable official base/top attributes. Many are
  temporary or open-sided structures. They stay outlined for source matching or
  manual authoring; no assumed-height boxes were generated for them.
- 35 native `GENERIC` source mesh parts (2,288,876 triangles) are retained as an
  optional reference. This category includes real structures as well as ground,
  vegetation and rough source fragments. No category-wide terrain projection or
  road-corridor deletion is applied. The context window selects whole triangles;
  it does not establish whole-object preservation for unclassified geometry.

The individual building candidates are kept intact: no flattening, imposed
roof height, road-corridor cuts or boundary chops. They are separate from the
window-selected `GENERIC` references. Original source files are not overwritten.

## Scene collections

| Collection | Use |
| --- | --- |
| `CLEAN_BUILDING_CANDIDATES` | Inspect the actual roof and wall silhouettes without facade imagery; default visible |
| `TEXTURED_BUILDING_REFERENCES` | Compare the source building textures at the same coordinates; enable instead of the clean variants |
| `NATIVE_GENERIC_REFERENCE` | Inspect unflattened structures and the source's defects; default hidden |
| `REVIEW_OUTLINES` | Blue outlines have individual candidates; orange outlines still need them |
| `ROAD_REFERENCE` | Source route centreline; not a modelled driving surface |
| `REFERENCE_TERRAIN` | Native 0.5 m DTM displayed at approximately 2 m spacing, with orthophoto layout imagery |

The two building-variant collections overlap deliberately. Enable one at a
time. The orthophoto terrain is a placement reference with baked imagery,
including roof images and shadows; it is not a finished ground material.

## Visual findings and production decision

Four renders under `previews/building_review/` compare clean overview, textured
overview with native `GENERIC`, driver forward, and driver reverse. Their hashes
are recorded in `reports/building_review_scene.json`.

The clean overview gives coherent volumes for the matched buildings and makes
the missing structures visible as outlines. Textured individual models include
stretched/blurry facades and a missing-image fallback. Including native
`GENERIC` restores many small structures in the aerial view, but the driver
views show torn walls, spikes, jagged ground/roadside fragments, and poor nearby
texture detail. **Raw native photogrammetry is rejected for direct foreground
production use in this state.** Its ability to fill an overhead view does not
meet the Route Twisk reference at driver height.

Use the clean candidates as source-linked bases after resolving their flags.
Reconstruct nearby temporary structures and roofs from suitable references;
author walls, shopfronts, railings, poles and vegetation separately. Preserve
native photogrammetry as reference or assess it individually for distant use.
Do not flatten all `GENERIC` objects or promote all of them as finished scenery.

The road is still source terrain/imagery in this scene. Proper widths, profiles,
continuous collision, junctions, kerbs and drainage remain a separate production
step. No KN5 is exported or installed by these commands.

## Rebuild and verify

From the repository root:

```powershell
python projects/hk01_kam_tin/scripts/prepare_building_review.py
python projects/hk01_kam_tin/scripts/prepare_generic_review.py
python projects/hk01_kam_tin/scripts/test_building_review.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python projects/hk01_kam_tin/scripts/build_building_review.py
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python projects/hk01_kam_tin/scripts/verify_building_review_scene.py
```

The source collector/preparer from `FULL_HONG_KONG.md` is a prerequisite.
Selected photo-model dependencies are extracted into ignored
`source/building_review_selected/`, with source archive SHA256 checks and member
CRC checks. Edited extracted files are preserved by refusing to overwrite them.
The glTF importer rejects remote/escaping dependencies and invalid indices.

Large meshes, textures, Blender scenes and renders stay local/ignored. Small
scripts, this guide, candidate summaries and scene-verification reports are
published to GitHub. Retain the Lands Department/CEDD/HKSAR Government and
OpenStreetMap source attribution with derived work.
