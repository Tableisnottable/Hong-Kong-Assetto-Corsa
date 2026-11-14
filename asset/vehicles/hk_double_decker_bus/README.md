# Hong Kong double-decker bus prototype

This folder documents a prototype low-poly Hong Kong-style double-decker bus designed as a lightweight Assetto Corsa modelling base. Generate the mesh locally with the command below; OBJ outputs are ignored by Git, so a fresh clone does not include the editable mesh.

## Files

- `hk_double_decker_bus.obj` — editable mesh source in Wavefront OBJ format
- `hk_double_decker_bus.mtl` — material definitions for the body, glass, trim, tire, and lights

## Notes

- The model is intentionally simple and low-poly for fast iteration.
- Dimensions are approximate and based on a standard Hong Kong bus silhouette.
- Use this source as a starting point for a higher-detail KN5 conversion in ksEditor / Blender.

## Regeneration

From the repository root:

```powershell
python .\tools\generate_hk_bus.py
```

The script writes a fresh OBJ and MTL pair into this folder.
