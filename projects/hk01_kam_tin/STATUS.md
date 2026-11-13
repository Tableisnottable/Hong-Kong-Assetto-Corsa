# Build status — November 13, 2026

**Version 0.3 full-loop test is installed for the user's own test.** Select **Hong Kong — Kam Tin Driving Test**, ID `hk01_kam_tin_test`, in **Practice, one car, clear daytime, start from pits**. The complete 3.445 km Kam Tin loop has adapted Lands Department scenery from eight source sheets and eight numbered blue test markers. This milestone covers the selected loop; the remaining regional network and whole Hong Kong are unfinished.

The native multi-model package contains 9 KN5 files, 7,609,218 triangles and 4,454 mesh nodes (1,795.7 MB total KN5). Embedded texture payload is 1,246.3 MiB, with complete mip chains for DDS BC1 source textures. This is a file-based estimate, not measured game VRAM or FPS. The ZIP is 1,005.4 MB. All generated assets and source downloads remain local.

Verified: source-sheet coverage for all 1,723 centreline samples; 12,061 road-support rays over seven positions across both lanes; maximum road-profile deviation 0.0423 m; 272 physical mesh payloads unchanged from version 0.1; all logical spawn/timing nodes unchanged; no degenerate exported triangles; no source-scenery triangles intersecting the protected 10.5 m half-width road corridor; binary/image structure checks; ZIP CRC; and installed-file hashes.

**Actual engine loading, driving and FPS remain untested.** The game was not launched. Road widths/profile, barriers and junction treatment are temporary. Source scenery has no vehicle collision and close-up photogrammetry can be rough. Missing source texture references: 1, handled with neutral fallbacks. No AI, traffic, night/rain tuning or multiplayer support is included. Neighbouring roads are scenery.

See `TESTING.md`, `validation_summary.json`, and local `driving_test/route_scenery/reports/`. The installed package is `release_route_scenery/content/tracks/hk01_kam_tin_test`; the editable scene is `blender/HK01_KamTin_FULL_LOOP_TEST.blend`. Version 0.1/0.2 files remain separate. The old Route Twisk project and historical OMSI repository were not modified.
