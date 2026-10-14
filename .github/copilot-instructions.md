# Copilot Instructions — Hong Kong Assetto Corsa

Guidance for working effectively in this repository. It builds a 1:1 scale Hong Kong road network and Hong Kong driving-test vehicles (categories 1/1A/2/2A/17/17A) as Assetto Corsa mod content.

## Repository layout at a glance

| Path | Purpose |
|------|---------|
| `config/map.json` | Authoritative map scope: id `hk_kowloon`, 1:1 metre scale, WGS84 source coords, layers, export settings. |
| `config/vehicles.json` | Source of truth for the 100-vehicle planning catalog (60 private / 25 commercial / 15 public-special). Buses, coaches, double-deckers and minibuses are **explicitly excluded**. Catalog entries are planning-only, not claims of authored/licensed assets. |
| `docs/production-plan.md`, `docs/map-production-plan.md` | Design rules: scale validation, pipeline order, quality gates, source/redistribution policy. |
| `tools/` | Main build pipeline: `fetch_hk_data.py`, `build_map.ps1`, `desktop_export.ps1`, Blender scripts in `tools/blender/`. |
| `server/` | AC dedicated server config + PS1 helpers (`start-server.ps1`, `validate-config.ps1`). |
| `extension/ext_config.ini` | CSP (Custom Shaders Patch) extension config for lighting. |
| `asset/assetto_corsa/` | Playable car/track packages (mesh-independent source packages; e.g. `hk_crown_comfort`, `tin_kwong_road`). |
| `auto/v1/` | Older/legacy automation: `build_and_deploy.ps1`, `scripts/process_csdi.py` (stub), `scripts/blender_export.py`, `cars/` (6 driving-test car skeleton dirs), `web/` (Leaflet CSDI geoportal). |
| `build/HP1C/` | Generated outputs + source manifests (`source_manifest.json`, `tile_manifest.json`, `routes.json`). Treat as derived data. |
| `car/` | Raw driving-test vehicle spec notes (Traditional Chinese text files per category). |
| `index.html`, `cars.html`, `script.js`, `styles.css` | Static "public worklog" site (no build step). |

## Build / data pipeline

There is **no test or lint suite** in this repository. Validation is manual and happens at the tool level (script exit codes, manifest checks, in-game checks).

Map build pipeline (start here for map work):

1. `python tools\fetch_hk_data.py` — downloads OpenStreetMap Overpass road data for the Tin Kwong Road corridor. It intentionally makes at most **one** network request (15 s min interval, 3 retries, local cache) and writes `build/HP1C/source/` (raw `roads.osm.json`, `roads.geojson`, `source_manifest.json`). Never add Google Maps scraping or batch Overpass hammering.
2. `tools\blender\generate_tin_kwong.py` — headless Blender script generating the road blockout. Run via `blender --background --python tools/blender/generate_tin_kwong.py`. Outputs `build/HP1C/tin_kwong_road/` (`*.blend`).
3. `tools\blender\export_tin_kwong_fbx.py` — exports scene to FBX for ksEditor; takes a `--output <path>` argument after `--`.
4. `tools\build_map.ps1` — orchestrates steps 1–3 and then requires **ksEditor** (the AC SDK editor, not on PATH by default) to convert FBX → `.kn5`. FBX→KN5 cannot run headless.
5. `tools\desktop_export.ps1` — interactive helper (asks for `EXPORT` confirmation, `-DryRun` supported) that opens Blender and ksEditor manually; useful when the automated path cannot find ksEditor.

Server helpers:

- `server\validate-config.ps1` — validates `server\cfg\server_cfg.ini` + `entry_list.ini` against required settings (NAME, TRACK `hong_kong_1to1`, UDP/TCP 9600, ≥1 `[CAR_n]` slot). Run after any server config change.
- `server\start-server.ps1 -ServerRoot <AC server dir>` — starts `acServer.exe` with the repo config; requires the mandatory `-ServerRoot` parameter.

Single-command checks:

```powershell
# Fetch/refresh road source data (cached)
python tools\fetch_hk_data.py

# Validate server config without starting the server
powershell -File server\validate-config.ps1

# Regenerate the map blockout
blender --background --python tools/blender/generate_tin_kwong.py
```

## Non-obvious conventions

- **Keep identifiers in sync.** The canonical map id is `hk_kowloon` (see `config/map.json`); the driving-test prototype uses `tin_kwong_road` / `hong_kong_1to1`. The same id must appear in Blender export, track folders, `models.ini`, server `TRACK=`, and manifests. `server_cfg.ini` currently uses `TRACK=hong_kong_1to1` while `config/map.json` uses `hk_kowloon` — don't silently "fix" these without checking which asset actually ships.
- **1:1 scale is a hard rule.** Source coordinates stay in WGS84 until the import step; convert to a local metric projection before mesh generation. Blender units = meters (`1 Blender unit = 1 meter`), transforms are applied before export, and any km/cm conversion error is a bug. Validate distances against ≥3 known reference measurements (≤1% tolerance).
- **Sector/tile discipline.** Never bake the whole city into one mesh. Split into streamable sectors (`sector_size_meters: 250` in `config/map.json`); keep spawn and timing lines in one always-loaded sector. The Tin Kwong Road sheet splits `.kn5` models into `11-SW-9D-1` / `11-SW-9D-2` only when a model exceeds 2 GB (`build/HP1C/tin_kwong_road/tile_manifest.json`).
- **Licensing is a hard gate.** Every dataset/asset needs source URL + licence + attribution recorded in a manifest. Prohibited: Google Street View exports, commercial game rips, unlicensed manufacturer CAD, ripped meshes/logos. Google Maps is manual-reference-only (never downloaded). `config/vehicles.json` requires `source_status: original_model_required` for every vehicle.
- **Vehicle data baseline vs final.** `asset/assetto_corsa/cars/hk_crown_comfort/data/*.ini` values (dimensions, mass, drivetrain) are a *baseline to validate* against the authored model — do not present them as final. No brand logos or unlicensed textures in skins; use replaceable badges/plates.
- **Mesh-independent car packages.** Car packages under `asset/assetto_corsa/cars/` are deliberately mesh-independent source packages: `.kn5` models get added at install time; the repo holds `data/`, `ui/`, README, and structure. Local install target is `content/cars/<id>/` and `content/tracks/<id>/` inside an Assetto Corsa install.
- **Headless Blender scripts** take `import bpy` at module scope and must run with `blender --background --python <script>`; they must not depend on the GUI. FBX axis conventions differ per pipeline stage: `export_tin_kwong_fbx.py` uses `axis_forward="-Z", axis_up="Y"`, while `auto/v1/scripts/blender_export.py` uses `axis_forward='Y', axis_up='Z'`.
- **Generated/derived outputs** live under `build/` (blockouts, manifests, FBX) and are partially gitignored (`*.fbx`, `*.obj`, `*.zip`, `*.blend1`, downloaded model dumps). `*.blend` files that ship (e.g. `track_check.blend`, `build/HP1C/.../*.blend`) are intentional review artifacts.
- **`auto/v1/` is legacy.** Its `process_csdi.py` is a stub and `build_and_deploy.ps1` hardcodes the author's local paths (e.g. `C:\Users\Table\...`, Blender 4.2, `kn5-conv.exe`). Prefer `tools/` for new work; don't extend `auto/v1` unless specifically asked.
- **Windows-only tooling.** Build scripts are PowerShell and depend on machine-specific absolute paths (Blender at `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe` or Steam Blender; ksEditor under the AC SDK). Scripts discover these via `Get-Command` first, then fall back to hardcoded paths.
- **Bilingual docs.** User-facing docs and UI mix English and Traditional Chinese (e.g. `lang="zh-HK"` in `auto/v1/web/index.html`; `ui_track.json` name/description are Traditional Chinese). Preserve existing language per file; don't translate content away from the project's established usage.
- **Driving-test routes** are sourced from published HK driving-test route anchors (see `asset/routes/tin_kwong_road.json` and the `ANCHORS` dict in `generate_tin_kwong.py`). Route IDs (`tin_kwong_1`/`2`/`3`) are stable — new geometry can be added without renaming routes.

## Workflow conventions

- Commit style uses conventional prefixes in the history (`feat:`, `fix:`, `docs:`, `refactor:`). Match this for new commits.
- Web pages in the repo root are a static "public worklog" (no framework, no build step). Keep them dependency-light.
- Before changing any `*.ini` that the game/server reads (`data/surfaces.ini`, `models.ini`, `server_cfg.ini`, `ext_config.ini`), run the corresponding validator where one exists (`server\validate-config.ps1`) and keep AC ini section/key naming intact.

## Task execution: small steps, commit and push

- Break every request into small, independently committable steps (one logical change per step: e.g. one script, one config, one doc update). Finish and verify one step before starting the next.
- Commit after each verified step using the repo's conventional prefixes (`feat:`, `fix:`, `docs:`, `refactor:`).
- Push to the current working branch after committing so work is backed up in the repo. Do not push directly to `main` — use the session branch and open a pull request for review.
- Never combine unrelated changes in one commit, and never leave finished work uncommitted at the end of a session.
