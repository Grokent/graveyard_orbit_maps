# Graveyard Orbit Maps — COW ABDUCTION

An original custom contract for **Graveyard Orbit**: a saucer/dome UFO
tractor-beaming a cow, built from **50,221 hex cells**.

![COW ABDUCTION](previews/ufo_cow.png)

## ⚠️ Disclaimer

This project is **100% vibe coded** and **100% the product of AI use**. It is an
unofficial fan project. I make **no claims of ownership** over Graveyard Orbit,
its code, assets, names, or anything derived from it. **All credit and all
rights belong to Anchorhead Games.** If you own the game, you are welcome to
use this map for private play. No game code or game asset files are distributed
here.

## Install (Windows and Linux are the same)

The release zip includes BepInEx, the loader plugin and the map — no compiler or
separate setup.

1. Close Graveyard Orbit.
2. In Steam, right-click **Graveyard Orbit** → **Manage** → **Browse local files**.
   That opens the game folder (the one containing `GraveyardOrbit.exe`).
3. Download the release zip:
   **[GraveyardOrbit-UfoCow-0.1.0.zip](https://github.com/Grokent/graveyard_orbit_maps/releases/latest/download/GraveyardOrbit-UfoCow-0.1.0.zip)**
4. Extract **everything** from the zip into the game folder that opened in step 2.
   It only adds files (`winhttp.dll`, `doorstop_config.ini`,
   `.doorstop_version`, `changelog.txt`, `BepInEx/`). **No original game file is
   replaced or modified.**
5. **Linux / Proton only:** add this launch option once (game → Properties →
   Launch Options). Windows needs no launch options:

   ```
   WINEDLLOVERRIDES="winhttp=n,b" %command%
   ```

6. Launch the game through Steam.

If you already use BepInEx, the bundled loader is the same 5.4.23.6 version and
is additive; the map itself lives in
`BepInEx/plugins/GraveyardOrbit.UfoCow/`.

## Play

New Game → **COW ABDUCTION** (first in the contract list). The ship starts on
the planet side of the cow.

- Four **gold-capped entrances** at the leg bottoms lead into a 3-wide black
  maze.
- The south is gold/blue and easy to break; the north is purple/pink and much
  tougher.
- 24 hidden rooms, 20 artifacts (power-up rolls), 120 glyphs (enough beacons
  for two players to open all 20 relic slots), 64 salvage crates and 298
  authored mod-material veins.

## Uninstall

Delete `BepInEx/plugins/GraveyardOrbit.UfoCow/`. Remove `winhttp.dll`,
`doorstop_config.ini`, `.doorstop_version`, `changelog.txt` and `BepInEx/` only
if you do not use any other BepInEx mod.

## Repo contents

| Path | What it is |
|---|---|
| `maps/ufo_cow.json` | map in the game's `MegastructureData` JSON format |
| `contracts/ufo_cow.contract.json` | contract metadata: bands, artifacts, beacons |
| `generate_map.py` | deterministic generator (silhouette, maze, layers, pickups) |
| `validate_map.py` | format + design validator |
| `loader/` | small BepInEx plugin that adds the contract at runtime |
| `previews/ufo_cow.png` | colour preview |
| `AGENTS.md` | full map/contract reference (layers, tiers, hex, rooms, bands) |
| `docs/MAP_BEST_PRACTICES.md` | reusable map-generation workflow and traps |

## Build from source (developers)

Requires a legitimate copy of the game, plus `unzip`, `curl` and Python 3
(Pillow only for the preview).

```bash
./setup.sh           # project-local .NET SDK + BepInEx download
./loader/build.sh    # builds the loader plugin
./loader/deploy.sh   # installs it into the local game folder
./package.sh         # rebuilds release/GraveyardOrbit-UfoCow-0.1.0.zip
python3 generate_map.py
python3 validate_map.py
```

Set `GAME_DIR` if the game is not in the default Steam library. The generator
is deterministic: same `--seed` and `--scale` produce the same map.

## License and credits

The project's own code and map are MIT licensed (see `LICENSE`). The release zip
bundles BepInEx, which is LGPL-2.1 (see `THIRD_PARTY_NOTICES.md` and
`licenses/LGPL-2.1.txt`).

Graveyard Orbit and all related content are © **Anchorhead Games**. This is an
unofficial, fan-made, AI-generated project with no affiliation with or
endorsement from Anchorhead Games. All rights to the game and its assets remain
with them.

Repository: <https://github.com/Grokent/graveyard_orbit_maps>
