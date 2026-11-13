# Required quality reference — Route Twisk RWE / Repack Test

Selected by the user on November 14, 2026. The quality target is the installed RWE/Repack map, not merely a loadable geographic blockout. No reference assets are reused, and the reference installation is unchanged.

## Current result

**The gap is not closed.** Version 0.5 is a comparison build. It improves specific materials, foliage silhouettes and visual safety rails, but it is not accepted as matching the reference. Blender previews are geometry/material-authoring evidence; they cannot establish Assetto Corsa lighting or gameplay performance.

The read-only reference audit found separate actual-tree and billboard-tree models, multiple leaf and bark materials, alpha-tested foliage/markings, multiple named road/ground textures, and dedicated barrier/roadside models. Its inspected main and roadside material setup mostly uses `ksPerPixel` and `ksPerPixelAT`; a complex shader alone is not the missing ingredient. The project instead needs coherent modelling and placement of the components visible from a car.

## Acceptance requirements

- **Road and markings:** believable aggregate scale, restrained repeating patterns, flush paint, realistic width/profile/camber, joined junction surfaces and correctly placed lane/edge markings. A generic seven-metre strip is provisional.
- **Roadside modelling:** real kerbs, drainage, pavement transitions, appropriate railings/guardrails, posts, lamps, signs and small fixtures. Their positions and dimensions must be checked against permitted geographic/reference data. Generic rails following test bounds do not satisfy surveyed roadside fidelity.
- **Vegetation:** convincing leaf scale/cutout edges, varied crown architecture, trunks and undergrowth. Avoid both angular photo blobs and repeated round hedge-like crowns. Generic replacement foliage needs further botanical and placement work.
- **Buildings and ground:** readable nearby facades; no source-photo stumps, melted ground fragments, gaps or obvious image boundaries; consistent local colour and scale. Flattening a photo mesh is an interim cleanup.
- **Driving:** continuous pavement in both lanes, stable junctions, safe pit entry/respawn, and collision that matches the visible roadside geometry. The retained coarse test-wall collider behind v0.5 rails is provisional.
- **Engine comparison:** same car, time/weather, resolution and graphics/CSP settings when comparing with the installed reference. No clipped-white surfaces, alpha foliage defects or intrusive scenery. Record a complete-lap frame-time/FPS result; 60 FPS remains a planning target.

## Version 0.5 changes and limits

New photographed asphalt and generic grass/rock texture, worn alpha-cut paint, composed leaf-spray atlas, eight authored tree-shape variants, photographed bark, welded/smoothed visual terrain, and authored folded W-beam visual rails with posts/bolts/reflectors. Original collision payloads and spawn/timing matrices are retained. Road/pit clearance and alpha-texture checks complement the earlier surface tests.

These changes do not finish junctions, kerbs, drainage, local streetscape or source-ground/near-building cleanup. Accurate roadside collision also remains to be modelled. The next focused production milestone should finish a representative 300–500 m section against this checklist before treating the whole loop as reference-quality or expanding the region. That milestone is not claimed as complete in v0.5.
