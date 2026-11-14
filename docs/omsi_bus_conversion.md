# OMSI Bus Conversion

`tools/build_omsi_families.py` converts the installed OMSI O3D body and wheel meshes for the KMB ATENU, ATEE, Dennis Dragon, and Scania families into local Assetto Corsa packages. It reads mass and the full engine torque curve from each source `.bus` and engine constant file, then uses the named installed AC bus as the starting physics and sound package.

The converter expects OMSI 2 at `A:\SteamLibrary\steamapps\common\OMSI 2\Vehicles`, Assetto Corsa at `A:\SteamLibrary\steamapps\common\assettocorsa`, and Python packages `numpy` and `Pillow`. Run one family at a time from the repository root:

```powershell
python tools/build_omsi_families.py atenu
python tools/build_omsi_families.py atee
python tools/build_omsi_families.py dragon
python tools/build_omsi_families.py scania
```

Packages are written to `outputs/<FAMILY>_playable/`. The script does not install them. Copy each resulting car folder from `content/cars/` into the AC `content/cars/` directory after closing AC. Large converted KN5 models, source textures, and sound banks are local outputs and are intentionally not tracked in this repository.

## Installed KMB cars

The current local Assetto Corsa installation has these six selectable cars:

| OMSI bus | Assetto Corsa car ID |
| --- | --- |
| ADL E200 | `kmb_e200_drivable` |
| ADL E6M | `kmb_e6m_drivable` |
| ADL E500MMC ATENU | `kmb_atenu_drivable` |
| ADL Enviro500 ATEE | `kmb_atee_drivable` |
| Dennis Dragon 9.9M | `kmb_dennis_dragon_9m_drivable` |
| Scania K230UB | `kmb_scania_k230ub_drivable` |

In Content Manager, choose **Drive > Single** (or an offline practice session), select a car by its displayed KMB name, choose a skin, then select a track and start the session. The destination boards are fixed to the included OMSI-derived skin artwork; the OMSI route keypad and route selection are not ported. Three-axle models use two physical AC axles, with the rearmost axle animated visually by CSP Lua.

E6M, ATENU and ATEE use the middle driven axle for native AC physics; their final axle rotates through a Custom Shaders Patch Lua animation. The Dragon uses its rear driven dual wheels for native physics and its intermediate axle is visual. Mirrors, cockpit controls, sounds, and the base AC suspension schema come from the donor package. These are adaptations; OMSI scripts are not executed in AC. In-game driving still needs to be tested on the target installation.

## E500 and Scania height and movement repair

ATENU, ATEE, Dragon and Scania builds now run `repair_omsi_bus_physics.py` after conversion. It places the converted model origin at the source `.bus` center-of-gravity height (`schwerpunkt`, 1.2 m for these sources) and midway between the two AC axles. It sets the suspension wheel origins and individual front/rear track widths to match, removes the inherited donor graphics offset, measures tire radii from the wheel meshes, and creates a convex collision hull with 0.30 m nominal ground clearance. This keeps the body, visual wheels and physics in one coordinate frame.

The Dragon repair also corrects the wheel hierarchy: OMSI `wh2/3` are intermediate single wheels, while `wh4/5` are the driven rear duals. It uses the selected M250E20 engine curve, three forward gears and source final drive. DIWA's hydraulic first and reverse cannot be expressed as fixed AC ratios; the existing adapted first/reverse ratios remain, with source locked second/third ratios. Its nominal tire contact is within 3 mm of the source ground plane. Live driving remains unverified.

The repair follows the engine and gearbox files actually listed under the source bus's `[constfile]`. ATENU previously used a different engine file; its selected curve reaches 1492.5 Nm. The three repaired buses use their source six-speed ratios and final drives. Automatic and AI shift thresholds stay below the end of each engine's usable torque curve. Missing referenced grip and coast LUTs are supplied locally. Donor turbo multiplication is removed because it would add boost to the imported engine curve.

Native AC suspension remains an approximation: it uses a 50/50 front/rear axle weight split and static spring preload calculated from mass and the source spring rates. Source axle positions and counts can disagree with the visible models (particularly Scania); the converted wheel meshes determine AC's two axle positions and tire radii. This is not a claim of a fully reproduced OMSI suspension or transmission controller.

To repair an existing converted package and install it, close AC first and run:

```powershell
python tools/repair_omsi_bus_physics.py <package-directory> --install
python tools/validate_omsi_bus_physics.py <package-directory>
```

The installer backs up the model and physics files, checks for independent installed edits, and records installed hashes in `road_contact_repair.json`. The validator checks wheel pivots against physics coordinates, model versus physical tire radius, nominal ground clearance, LUT references, shift torque, and installed file hashes. These offline checks do not establish live handling, dynamic tire contact or road collision behavior. Start a fresh session to retest forward/reverse movement and check the tires from an external view on flat road and Route Twisk slopes.
