# Build status — November 13, 2026

**Current milestone: version 0.2 is installed, with real CSDI scenery on one 750 × 600 m tile.** It is named **Hong Kong — Kam Tin Driving Test**, ID `hk01_kam_tin_test`, with a 3.445 km solo loop. Actual game loading, driving and FPS tests remain pending the user; the game was not launched. Surrounding regions remain blockout.

The current KN5 has 1,167,858 triangles, 1,033 mesh nodes and 270 embedded textures/materials. Independent parsing found zero degenerate triangles; all images decoded. All 272 physical mesh payloads and all spawn/timing matrices match version 0.1. No imported non-terrain scenery triangle intersects the checked 10.5 m road corridor. Installed hashes match the package. See `driving_test/csdi_sample/reports/`.

The source ZIP (312.6 MB), KN5 (504.0 MB), install ZIP (450.2 MB), Blender scene, source textures and arrays stay local. GitHub receives scripts, documentation, small configuration and validation summaries only. See `PUBLISHING.md`.

Known limits: only tile 6-NE-12D has real scenery; rough close-up photogrammetry, one missing source texture fallback, temporary road width/profile and synthetic barriers remain. Visual terrain is blended near the road and tile edge; imported scenery has no vehicle collision. The native SDK graphics check could not initialise and does not establish engine acceptance.

The driving test follows Kam Sheung Road, Tung Wui Road, Kam Po Road and Shek Tin Road. It uses temporary 7 m road width, a smoothed profile, a separate pit apron, synthetic safety barriers, basic lane markings and simple context buildings. No AI opponents or traffic are included. Use solo **Practice** in clear daytime. See `driving_test/reports/` for current results and `release/content/tracks/hk01_kam_tin_test/TEST_README.txt` for first-run instructions.

| Item | Verified result |
|---|---|
| First region | Kam Tin / Shek Kong, 6 × 6 km |
| Scale | 1 Blender unit = 1 metre |
| Master inventory | 78,674 mapped road parts, including access-review categories |
| First-region road references | 2,289 segments |
| Building masses | 4,562 objects; 4,524 have estimated heights |
| Grade-separated road review | 149 bridge, tunnel or non-zero-layer segments |
| Road alignment verification | 343,192 triangle centroids checked against the terrain mesh |
| Reference strip clearance | Approximately 0.22 m throughout the checked faces |
| Degenerate road triangles | 0 in the delivered file |
| Terrain gaps | No nodata samples in the selected regional crop |
| Saved scene verification | Passed; all checked coordinates finite |
| Game launch / FPS test | Not performed |
| Test-loop KN5 export | Produced; user engine/driving test pending |

The road-part counts are source geometry counts, not counts of distinct streets. Mapped line lengths must not be reported as official Hong Kong road mileage.

Fixed during this build: incomplete regional boundary assembly, motor-access tag precedence, lost road-node references, road strips intersecting the terrain, a low building buried by a slope, two zero-area triangle fragments, and dependence on an enabled Cycles add-on when opening the delivered scene. The saved scene uses Blender's built-in Workbench renderer; the included preview was rendered separately with Cycles.

The next production milestone is the user's engine/driving/FPS test, followed by road-profile refinement and further real-scenery tiles. The full Hong Kong objective remains a staged regional project. The historical OMSI repository was inspected read-only; no finished high-detail model data for this loop was found and no source-repository files were edited.

See `reports/validation.json`, `reports/blender_verification.json`, and `reports/blender_build.json` for the actual check results. Source inventory, checksums, review queue and attribution are retained alongside the project.
