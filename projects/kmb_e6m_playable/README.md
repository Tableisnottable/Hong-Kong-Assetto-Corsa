# KMB E6M Assetto Corsa Configuration Prototype

This folder contains the small text configuration changes for the local KMB E6M Assetto Corsa prototype. It is not a complete car download.

## Install

Copy the `content/cars/kmb_e6m_drivable` folder into your Assetto Corsa `content/cars` directory, merging it with a separately obtained copy of the bus. Back up the existing car folder first.

The large model, textures, and sound bank are not included. The original OMSI bus files and display artwork are also not included. This config patch will not create a drivable car by itself.

## Scope and limits

- The mass, wheel diameter, and engine curve were based on values read from the user's local OMSI E6M installation. Assetto Corsa handling remains an approximation and still needs an in-game test.
- Route 51 destinations are supplied as skin configuration. This does not convert OMSI's keypad, scripts, or dynamic destination display system.
- The fourth axle's in-game wheel animation has not been verified.
- No permission to redistribute the original bus model, artwork, sounds, or OMSI files is implied by this configuration-only folder.

The route skins reference the matching display textures in the separately installed local car. Since those textures are intentionally omitted here, the route signs will only appear when the required textures are already present locally.
