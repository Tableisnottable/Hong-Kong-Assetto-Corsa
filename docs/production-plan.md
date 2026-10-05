# Production plan

## 1. Map boundary and scale

The first release is the road corridor between Tsim Sha Tsui, Mong Kok, and
Kowloon Bay. The boundary is intentionally a corridor rather than all of
Kowloon so that the first playable build can be finished and tested.

The map must remain 1:1:

- Keep source coordinates in WGS84 until the import step.
- Convert to a local projected coordinate system before mesh generation.
- Use meters for Blender units (`1 Blender unit = 1 meter`).
- Preserve road widths from source data where available; mark inferred widths
  in the source manifest.
- Keep the map origin near the first playable sector to avoid floating-point
  drift.

The authoritative scope is [`config/map.json`](../config/map.json).

## 2. Recommended map pipeline

1. Download an extract from OpenStreetMap for the configured boundary.
2. Keep the untouched extract in `source/gis/raw/` and record its date and
   attribution.
3. Convert roads, junctions, buildings, terrain, and traffic signals into
   normalized source layers.
4. Generate a Blender greybox with separate collections for roads, curbs,
   buildings, props, vegetation, and collision.
5. Assign Assetto Corsa material names and export sector meshes.
6. Generate `data/surfaces.ini`, AI lines, timing sectors, and cameras only
   after the greybox is driveable.

Do not bake the whole city into one mesh. Use sectors and streamable-sized
chunks so that visibility, collision, and iteration remain manageable.

## 3. Vehicle pipeline

The project needs many traffic vehicles, but they should be added in batches.
The target traffic mix is 60% private cars, 25% commercial vehicles, and 15%
public or special vehicles. The 100-car catalog in
[`config/vehicles.json`](../config/vehicles.json) is the planning list:
60 private cars, 25 commercial vehicles, and 15 public or special vehicles.
Buses, coaches, double-deckers, and minibuses are explicitly excluded from
this project. Catalog entries are not claims that all models are already
authored or licensed for redistribution.
Each vehicle should have:

- original source geometry or a redistribution-compatible license;
- a road-going LOD chain;
- a separate collision mesh;
- working suspension, steering, lights, and damage anchors;
- interior and exterior cameras;
- an Assetto Corsa `data` folder with verified dimensions and mass;
- replaceable materials for badges, plates, and taxi markings.

The initial hero vehicle is the Hong Kong Toyota Crown Comfort taxi. Create it
as an original model from licensed reference, with generic replaceable badges
until branding permission is available. The vehicle manifest in
[`config/vehicles.json`](../config/vehicles.json) is the source of truth for
the intended fleet and implementation order.

## 4. Quality gates

### Map

- A known-distance test segment measures within 1% of its source distance.
- Road collision has no gaps at junctions.
- The player can complete a loop without leaving the intended drivable area.
- AI lines and timing sectors are generated from the final road surface.
- Night lighting and traffic signals are tested separately from daylight.

### Vehicles

- Wheelbase, track width, and overall dimensions match the reference within
  the tolerance recorded in the manifest.
- The car starts, steers, brakes, shifts, and lights correctly in-game.
- LODs and texture sizes are tested in a populated scene, not only alone.
- No source asset with incompatible redistribution terms is included.

## 5. Suggested work order

1. Lock the OSM boundary and gather attribution.
2. Build the road-only greybox.
3. Add collision, timing, and a test AI line.
4. Add terrain and landmark massing.
5. Build the taxi and validate the car export independently.
6. Add common Hong Kong traffic vehicles in priority batches.
7. Replace greybox landmarks with optimized authored assets.
