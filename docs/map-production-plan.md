# Hong Kong 1:1 map production plan

## Goal

Create a drivable Assetto Corsa world at 1:1 scale using metres as the world
unit. The first release should prioritize a continuous road network, stable
collisions, and recognizable landmarks over dense decorative detail.

The canonical track identifier is `hong_kong_1to1`. Keep this identifier in the
Blender export, `content/tracks` folder, server configuration, and release
archives.

## Recommended initial boundary

Use a deliberately staged boundary so the project can ship an early playable
build:

- **Phase 1:** Hong Kong Island urban core and a continuous waterfront loop.
- **Phase 2:** Kowloon connection and the harbour crossing.
- **Phase 3:** New Territories, Lantau, and outlying islands where source data
  and performance budgets allow.

The exact boundary must be recorded as a polygon in the source-data manifest
before modelling starts. Do not infer a 1:1 claim from visual scale alone:
validate distances against at least three known road or coastline measurements.

## Coordinate and scale rules

- Use a projected metric coordinate reference system for authoring; do not
  model directly in latitude/longitude.
- Choose one local origin near the phase-1 boundary and document its source
  coordinates in the project metadata.
- Keep the Blender scene in metres and apply object transforms before export.
- Split the world into streamable sectors. Keep the player spawn and timing
  lines in one always-loaded sector.
- Preserve a high-resolution source mesh outside the game export so collision
  and render meshes can have separate budgets.

## Asset pipeline

1. **Reference manifest:** Record source URL, licence, capture date, coordinate
   system, and attribution for every dataset.
2. **Terrain:** Generate a tiled heightfield, repair water boundaries, and
   simplify a dedicated collision terrain mesh.
3. **Road graph:** Import road centre lines, clean junction topology, and assign
   lane widths, elevations, and driving direction manually at complex junctions.
4. **Road surface:** Build render, physical collision, and AI-line geometry as
   separate outputs. Use Assetto Corsa surface materials consistently.
5. **Buildings and landmarks:** Start with blockout volumes, then replace
   landmarks and skyline silhouettes with original or properly licensed assets.
6. **Traffic-free driveability:** Add guardrails, curbs, walls, signs, and
   collision proxies before adding small props.
7. **AI and timing:** Create a reversible main loop, pit/spawn positions, and
   timing sectors. Validate each sector in-game.
8. **Packaging:** Export to `content/tracks/hong_kong_1to1`, test on a clean
   client, and archive the exact source manifest with each release.

## Quality gates

### Scale

- Long-distance checks differ by no more than 1% from the reference measurements.
- Road widths and lane spacing are measured in metres, not eyeballed.
- No accidental kilometre/centimetre conversion exists in the export pipeline.

### Driving

- Every public spawn is on a flat, collision-safe surface.
- No known road segment has a missing collision mesh, invisible wall, or
  unrecoverable void.
- The server can load the track with the same identifier used by the client.

### Performance

- Test at the intended server/client view distance, not only in the editor.
- Keep sector boundaries away from junctions where possible.
- Profile draw calls, texture memory, and collision complexity before adding
  decorative detail.

## Open decisions to record before production

- Final phase-1 boundary polygon and local origin.
- Source datasets and their redistribution licences.
- Target client performance tier and minimum GPU memory.
- Whether the server is public, passworded, or community-only.
- Weather, time-of-day, CSP/Sol/Pure support policy.
