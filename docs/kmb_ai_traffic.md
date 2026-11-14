# KMB AI buses

All six installed conversions are listed in `config/kmb_ai_buses.json`.
Large vehicle models, textures and sound banks remain local.

## Content Manager opponents

Run after installing the converted cars:

```powershell
python tools/prepare_kmb_ai_grid.py --install
```

This audits the installed models, wheel pivots, colliders, skin IDs, sounds,
physics LUT references, forward/reverse gears and torque at AI shift RPM.
It installs **KMB - All 6 Buses** in Content Manager's **Race Grids** presets.
It does not launch the game or change the current race/player selection.

In Content Manager select **Drive > Single > Race**, choose your player car,
select the original **Route Twisk / TAI MO SHAN (HK51 - 66 Pits) v1.0** layout,
and load **KMB - All 6 Buses** in the opponent grid presets. Start with six
opponents, zero aggression and a one-lap test. The original uphill/downhill
traffic layouts also contain AI splines. The repack test track does not yet
have a verified AI spline; do not select it for this native opponent test.

`--align-tracks` optionally backs up and corrects front/rear suspension track
widths to the installed wheel hubs, leaving the other suspension settings
unchanged. This corrected the E200's approximately 11 mm rear pivot mismatch.
AC must be closed for this option. The normal audit is read-only for the cars.

Local `outputs/KMB_AI/native_ai_validation.json` records the results. A pass
means the files are consistent; it does not verify live AI movement, cornering,
road contact or performance. The six-bus preset uses the existing default KMB
skins and destination artwork. It does not simulate OMSI passenger service.

Preset schema reference:
[AcTools RaceGridViewModel](https://github.com/gro-ove/actools/blob/master/AcManager.Controls/ViewModels/RaceGridViewModel.cs).
