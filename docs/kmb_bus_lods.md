# KMB bus LODs

All six registered buses have generated LOD 1, 2, 3 and 4 in addition to the
unchanged full-detail LOD 0: E200, E6M, E500MMC ATENU, Enviro500 ATEE, Dennis
Dragon 9.9M and Scania K230UB. Native cars and Traffic Planner use separate
model coordinates and separate sets of reduced models.

| Level | Native AC distance | Traffic Planner distance | Maximum embedded texture size |
| --- | --- | --- | --- |
| 0 | 0–40 m | 0–80 m | Original |
| 1 | 40–90 m | 80–140 m | 512 px |
| 2 | 90–180 m | 140–250 m | 256 px |
| 3 | 180–350 m | 250–450 m | 128 px |
| 4 | 350–2,000 m | 450 m onward | 64 px |

The cockpit remains on the original model. LOD 2 removes small interior
fittings; LOD 3 also removes seats and dashboard detail. The body, glazing,
wheel pivots and destination screens are retained. Meshoptimizer reuses
source vertices with their normals, UVs and tangents, locks mesh extremes,
and applies an increasing error budget at each level. Each saved model is
read back to check geometry, textures, overall bounds, screen payloads,
unchanged animation pivots and a strictly decreasing triangle count.

Install prerequisites once:

```powershell
python -m pip install numpy Pillow luaparser lupa
npm install --prefix outputs/KMB_20MB/deps meshoptimizer@1.3.0
```

Stage native models without changing the game:

```powershell
python tools/build_kmb_bus_lods.py
```

The command prints the timestamped run directory and saves `validation.json`
there. After AC is closed, install that staged run with:

```powershell
python tools/build_kmb_bus_lods.py --resume outputs/KMB_LODS/RUN_DIRECTORY --install
```

`--resume` reads and revalidates all four staged models against the current
main model. Use it only for the same source model. If the main model changed,
build a fresh run. Installation backs up changed files inside the run folder,
copies all four models before switching `data/lods.ini`, checks installed
hashes and verifies that the original main KN5 is unchanged.

Stage traffic models with:

```powershell
python tools/build_kmb_planner_traffic.py
```

With AC closed, `python tools/build_kmb_planner_traffic.py --reuse-lods --install`
revalidates this traffic build's staged LODs and installs them along with backed-up Planner
patches. The optional `kmbLods` definition adds distance selection only to
these buses. A Lua helper loads levels on demand, caches them for reuse and
shows only the selected model; the existing near-car physics, body motion,
extra-wheel animation and full-detail pool remain in use. Stock traffic
definitions keep the existing two-level path. CSP updates may replace these
patches; check compatibility and rerun the installer if needed.

Validation:

```powershell
python tools/test_kmb_lods.py -v
python tools/validate_kmb_planner_traffic.py
```

The Lua tests exercise exact distance boundaries, return trips through the
bands, cached reuse, stock cars, full-detail ownership and failed model loads.
The installed traffic validator must be run **after** installation; staged
models are already read back by the builder. Offline checks and Blender
renders do not establish in-game switching, frame rate or appearance.

Large KN5 files, render images and backups remain local under `outputs/`.
Only source and documentation belong in Git. Adding LODs reduces distant
rendering cost; the original main models and audio still prevent these
installed bus folders from meeting the earlier 20 MB total-size target.
