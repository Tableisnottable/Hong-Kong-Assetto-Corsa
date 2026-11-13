# Small-files GitHub policy

This project is published under `projects/hk01_kam_tin` in the existing `Hong-Kong-Assetto-Corsa` repository. The repository copy contains selected text sources and validation summaries, not the locally installed mod.

Do not commit raw OSM/PBF/GIS inventories, terrain arrays, downloaded metadata containing download-key query strings, source model archives, extracted textures, Blender files, FBX/GLTF models, KN5 files, renders, package ZIPs, dependency folders, or game-install copies. Keep these local. No Git LFS or release-asset upload is part of this request.

Every new tracked file in this project must be below 1 MiB. Use `git add` with the explicit project path, inspect the staged name/size list, scan for credential strings and large file extensions, and confirm that only this project's commit is ahead of the fetched remote before pushing. Existing unrelated repository assets are outside this publishing change.

The tiny `track_config` files are reference configuration only; they require the generated KN5 and textures inside the local package before the track can load. `driving_test/source/test_loop_source.json` retains the selected loop's source references and coordinates. Current upstream downloads may differ from the pinned November 2026 hashes.

The user loaded/drove v0.3 but rejected its appearance. No v0.4 engine result or complete-lap FPS benchmark is claimed. Validation in `validation_summary.json` covers the exported binary, textures, physical-mesh preservation, spawn matrices, protected road corridor and installed file hashes.
