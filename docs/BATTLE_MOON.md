# BATTLE MOON (`battle_moon`) — design notes

A second custom contract for Graveyard Orbit: a planet-killer battlestation
seen in **3/4 view from below-right**, built from **59,819 hex cells**. It is an
original map in the same `MegastructureData` format as COW ABDUCTION, generated
by `generate_battle_moon.py` and checked by `validate_battle_moon.py`.

Deterministic:

```bash
python3 generate_battle_moon.py      # scale 1.0, seed 0xB47713
python3 validate_battle_moon.py
```

## Design brief

| Feature | Implementation |
|---|---|
| View | orthographic sphere, camera 10° below the equator and 20° to the right; meridians converge at the visible south pole |
| Black layout | **31.9% layer 1**: black grout between every hull panel, open panel bays, and the wide equatorial trench |
| Hull panels | 10° latitude × 11.25° longitude cells (two per 22.5° sector); black grout is 1.1° wide on each joint |
| Open bays | 8% of panels are fully open, 8% have a half-open recess; together they are 24% of all black |
| Equatorial channel | latitude band `|lat| ≤ 2.2°`, **98.8% layer 1**, about 10 cells wide, running limb to limb |
| Trench lips | `2.2° < |lat| ≤ 3.7°` in gold L4 |
| Entrances | 2 gold-capped mouths, one at each trench end on the limb |
| Main weapon dish | centre at 22°N, 5°W, angular radius 15°: projects to **(-0.38, +0.50)**, i.e. north of the equator and left of centre |
| Dish layers | pink core, gold core ring, blue basin with 8 gold ribs and a groove, gold rim, thin purple halo |
| Pickups | 29 artifacts, 140 glyphs, 96 crates, 399 specials, 32 rooms, $1000 start |

## The 3/4 projection

Each cell inside the disc is back-projected onto a unit sphere:

```
u = x / R,  v = -y / R,  w = sqrt(1 - u² - v²)
p = u·right + v·up + w·forward
lat = asin(p.y),  lon = atan2(p.x, p.z)
```

with the camera basis built from `CAM_LAT = -10°`, `CAM_LON = +20°`. The
silhouette is still a circle (as it must be for a sphere), but everything on the
surface is foreshortened:

- the equator arcs above the disc centre and runs from limb to limb;
- longitude seams curve and converge at the south pole near the bottom limb;
- the dish becomes an ellipse in the upper-left quadrant.

Sector identity is the visible longitude, eight bands of 22.5°. Latitude rings
for the palette are `lat > +20°` (north), `lat < -30°` (underside), and mid.

## Black panelling

Layer 1 is used as structure, not as a maze:

- **Grout:** every 10° latitude line and every 11.25° longitude line is a
  1.1°-wide black joint. The joints meet at the panel corners, so the whole
  grout network is one connected component.
- **Open bays:** a deterministic hash opens 8% of panels completely (black
  interior) and gives another 8% a half-open recess from their western edge.
  The plates still read as a grid; the bays read as unplated or open sections.
- **Trench:** the equatorial band is much wider than the grout, so it remains
  the dominant channel.
- **Cleanup:** the grout converges at the poles and can shed tiny fragments at
  the limb; the generator prunes every black component except the main network,
  so the validator's single-component requirement always holds.

Result: 19,080 black cells (31.9%). 76% of that black is grout or trench and
24% is open panel interiors.

## Sector palettes

Every sector uses the same rules (underside blue/gold, north pink/purple) with
different proportions, so the hull changes as you orbit it:

| Sector | Underside | North |
|---:|---|---|
| 0 (west limb) | 51% gold | 55% purple |
| 1 | 14% gold | 92% pink |
| 2 | 37% gold | 50% pink |
| 3 | 10% gold | 67% pink |
| 4 | 90% gold | 79% pink |
| 5 | 40% gold | 54% purple |
| 6 | 84% gold | 80% purple |
| 7 (east limb) | 29% gold | 73% pink |

Each panel is one solid layer chosen from its sector/ring weights, so the plate
colour changes at the grout, not inside a plate.

## Dish

- **Core:** L3 pink, 3.5° angular radius, 100% of the sampled core.
- **Core ring:** L4 gold at 3.5–4.4°.
- **Basin:** L2 blue at 4.4–12.4° with eight gold radial ribs and a gold groove
  at 9.8°; 67% of the sampled basin is blue.
- **Rim:** L4 gold at 12.4–15°, 100% of the sampled rim.
- **Halo:** L5 purple at 15–16.2°, separating the dish from the gold plates.
- **Focus chamber:** a 9-cell hidden room inside the core holding one artifact.

At 22°N the dish sits above the trench in the image and is foreshortened toward
the upper-left limb, which is what a 3/4 underside view does to a northern
feature.

## Pickups (reference-scaled for ~60k cells)

| Pickup | Count | Why |
|---|---:|---|
| Artifacts (`meta_2`) | 29 | power-up rolls, one per hidden room |
| Glyphs (beacons) | 140 | 2 players × 20 relics × 3 beacons = 120, plus slack |
| Salvage crates (`roomGreen`) | 96 | money crates |
| Authored specials | 399 | clustered veins: 150 gold, 120 red, 80 blue, 50 green |
| Hidden rooms | 32 | 7–19 cells, ≥3 cells from any black cell |
| Starting money | **$1000** | `startingMoney` |

Band `special1..meta1` counts are all zero: the veins are authored. Bands still
seed dormant enemies, scaled up ~20% from COW ABDUCTION. Gold veins sit on the
underside, blue/green on the upper hull (mean screen y 0.72 vs 0.38 / 0.23).

## Validation results

```
layer-1 share: 31.9% (target 30-36%)
trench       : 2,889 cells, 98.8% black, spans -138..138
black layout : 76% grout/trench, 24% open panel bays
entrances    : 2 gold-capped trench mouths
tunnel network: 19,080 cells, connected
gradient     : underside 100% L2/L4, north 100% L3/L5
dish         : 3,051 cells, centroid (-0.38, +0.50)
dish layers  : core 100% pink, basin 67% blue, rim 100% gold
rooms        : 32 rooms, 8-19 cells, >= 3 cells from black
beacons      : 140 glyphs
starting money: $1000
```

Layer mix: L1 31.9%, L2 22.5%, L3 8.3%, L4 24.1%, L5 13.2%.

The validator also checks each sector's underside is ≥55% blue/gold and north
≥55% pink/purple (dish excluded from the sample), both easy layers appear on the
underside and both hard layers in the north, the dish is above the equator and
left of centre, gold veins sit below blue and green veins on screen, and both
entrances reach the main layer-1 network.

## Loader status

The bundled BepInEx plugin injects both `ufo_cow` and `battle_moon` from
`maps/` + `contracts/` in its plugin folder. `loader/deploy.sh` copies both
pairs. Restart the game after regenerating; the map JSON is read at startup.

## License / provenance

Original generated geometry, 100% AI-assisted. Graveyard Orbit and all related
content belong to Anchorhead Games. No game code or game assets are stored in
this repository.
