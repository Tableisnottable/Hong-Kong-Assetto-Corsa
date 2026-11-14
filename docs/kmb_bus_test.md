# Test the six installed KMB buses

In Content Manager select **Highlands Short (KMB bus spacing)**, then choose
E200, E6M, E500MMC ATENU, Enviro500 ATEE, Scania K230UB or Dennis Dragon.
Start with **Practice, no opponents** to test forward, reverse, braking and
restarting from a stop. Automatic shifting and clutch assistance are already
enabled in the inspected user settings. With keyboard controls, accelerate
with **W**, brake with **S**, and release **Space** (handbrake).

For a mixed-bus test, use **Race** and the **KMB - All 6 Buses** opponent preset.
The new Highlands layout supports **12 total vehicles**. Refresh the track list
or restart Content Manager if the layout does not appear.

The normal Highlands Short layout has roughly 8 m between adjacent pit origins;
the E500 ATENU's collision body is roughly 11.76 m long. The separate bus layout
retains every second original pit bay and alternate grid rows. Its 12 pit bays
and 12 grid slots pass an overlap check using conservative collision boxes
covering all six buses with a 0.5 m separation margin. Road meshes and the AI line
come from the installed track. The original Highlands layout is unchanged.

To regenerate the separate local layout, with AC closed:

```powershell
python tools/prepare_kmb_test_layout.py --output <local-output-folder> --install
```

This removes a confirmed spawn-overlap condition. It does not establish that
every reported E500 stall has the same cause. The inspected earlier Highlands
session recorded a player ATENU lap, but the user's sticking report still needs
a fresh test. Engine/gear ratios and wheel-pivot checks pass offline; no live
test of the updated layout has been run by the conversion tools.

## Choose the destination

Close AC and double-click `tools/set_kmb_bus_display.cmd`. Choose a bus or **all**,
enter the route number, and choose the correct terminus. In Content Manager,
refresh skins and select **KMB CUSTOM**. This uses the installed OMSI HOF and
artwork. Included presets are **Not in Service**, **51 Tai Mo Shan**, **51 Sheung
Tsuen** and **51 Tsuen Wan (Nina Tower)**.

E200 and ATENU use amber, E6M uses white, ATEE and Scania use green, and Dragon
uses a printed rollblind appearance. The selected source variant determines the
style; this is not a claim that every real-world bus in a family has that colour.
When exact artwork is absent, the tool records and prints its adaptation.
The installed Gorba bitmap library is missing; Scania uses shared green OMSI
artwork. Some Dragon destinations and number boards are rendered from route text.

All six Traffic Planner models have rebuilt embedded displays. Their default
destination is NIS; native opponents use their selected car skin. To use a custom
destination for Traffic Planner, first set it for **all** buses, then run:

```powershell
python tools/build_kmb_planner_traffic.py --skin kmb_custom_route --output <local-output-folder> --install
python tools/validate_kmb_planner_traffic.py --output <local-output-folder>
```

Restart the session to load rebuilt traffic models. The OMSI keypad, passengers,
ticketing and full electrical/door logic are not ported. Traffic Planner has its
own models and does not run the buses' cockpit scripts or sound banks.

All generated models, images, sounds and local backups stay off GitHub. Only
small tools and documentation are published.
