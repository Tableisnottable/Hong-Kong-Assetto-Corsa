# KMB Speedometer Calibration

`tools/repair_kmb_speedometers.py` installs the OMSI source speed curve as the
Assetto Corsa analogue LUT and synchronizes the Lua curve for E200 and E6M,
whose KN5s contain a `KMB_SPEED_MOTION` pivot. The AC digital readout shows
vehicle speed in km/h; the needle interpolates `abs(car.speedKmh)` against the
source curve in those same units.

E200, E6M, ATENU and ATEE use their OMSI `cockpit_tacholinie` /
`cockpit_tachowinkel` calibration (0-120 km/h, 0-252 degrees). Dragon uses
its own source-specific knots, including 20 km/h -> 30 degrees and 60 km/h ->
115 degrees. Scania's source model uses
`cockpit_tacholinie` normalized to 0-1 and multiplies it by 248 degrees, so its
calibration is 0 km/h -> 0 degrees, 20 -> 12.4, and 110 -> 248. Beyond the last
source knot the curve clamps to its final angle.

Run `python tools/test_kmb_speedometers.py` for source-knot and quarter-km/h
sampling checks. Preview planned files with
`python tools/repair_kmb_speedometers.py --dry-run`. Running without
`--dry-run` installs the changes, refuses to write while `acs.exe` is running,
and backs up installed files under
`C:\Users\Table\Documents\Codex\backups\kmb_speedometers`.

Only E200 and E6M have a separate animated speed needle. The installed ATENU,
ATEE, Dragon and Scania KN5s expose a speedometer mesh but no `ARROW_SPEED` or
`KMB_SPEED_MOTION` transform node. Their analogue LUTs now contain source
calibrations, but their mesh needles cannot be animated by a LUT alone. Fixing
the four static needles requires model pivots or a verified runtime mesh-pivot
implementation, outside this configuration-only scope. The installed Scania
cockpit Lua is a copied E200 script with missing-node references and retains
the E200 runtime curve; it is left untouched. Its source package curve is
calibrated, but still cannot animate the static KN5 mesh. No in-game runtime
test is performed.
