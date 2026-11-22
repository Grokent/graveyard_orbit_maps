# Map generation — best practices and fast path

Practical notes from building COW ABDUCTION. None of this is a hard rule; it is
the stuff that saved time, plus traps that cost time. For the game's data model,
read `AGENTS.md` first; this file is the workflow.

## TL;DR checklist

1. **Measure a reference map first** (layer mix, rooms, pickups) instead of
   guessing. See "Analysis" below.
2. Copy the current generator pattern, keep a fixed `--seed`, and make the map
   deterministic.
3. Decide the **silhouette** and tune `--scale` until the cell count is in
   range (49k–52k for a 50k contract).
4. Carve the **maze** and make connectivity validation fail loudly.
5. Assign **layers by a north/south gradient** plus coherent patches, not
   per-cell noise.
6. Place **entrances with gold caps** and test them; straight lines are not
   paths.
7. Author **pickups in clusters**; set procedural material counts to zero.
8. Run `validate_map.py` on every regeneration.
9. Deploy, restart the game, start a **new** contract (old saves keep their
   destroyed-cell history).
10. Check `BepInEx/LogOutput.log` for `[ufocow] injected` and the
    `[MiningSortie]` counts.

## Analysis first

Measure these from a reference contract before designing a new one:

- cell count and `q`/`r` bounds
- layer histogram
- `alt` histogram (authored specials/enemies)
- hidden-room count and room sizes
- green shard count
- artifact / glyph / salvage counts (the runtime log is the easiest source)

Useful reference numbers observed for Graveyard Orbit:

| Reference | Cells | L1 | L2 | L3 | L4 | L5 | Rooms | Pickups |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `structure_005.json` | 10,262 | 43% | 32% | 16% | 6% | 2% | 0 | no green |
| base 25k contract (log) | ~25,055 | — | — | — | — | — | 20 | 12 artifacts, 58 glyphs, 40 crates, 166 specials |
| merged 50k (reference) | 50,499 | 56% | 12% | 7.7% | 11% | 13% | 40 | 336 specials |

COW ABDUCTION targets 25–35% black, so it intentionally uses far less L1 than
the merged reference.

### Analysis traps

- **Never `zip()` a `set` of cells with the JSON's parallel arrays.** Set order
  is arbitrary, so the layer/alt mapping will be silently wrong. Build
  `cells = list(zip(q, r))` and then `dict(zip(cells, layer))`.
- `q` and `r` are axial; screen/pixel x is `q + r*0.5`, not `q`.
- A cell's `r` is the latitude key for gradient checks (larger `r` = south /
  planet side).
- The runtime log is a good source for actual painted counts; authored counts
  in `alt` are not the whole story.

## Generator shape

Keep the generator single-file and deterministic:

```python
def build(scale, seed) -> dict: ...
def write_outputs(data): ...
```

Constants worth exposing/tuning:

| Constant | Effect |
|---|---|
| `MAZE_SPACING` | smaller = more tunnel cells, higher black % |
| `PLAZA_CHANCE` / `PLAZA_RADIUS` | extra black open areas, higher black % |
| dilation radius (fixed at 1) | corridor width; radius 1 = 3 cells |
| `LOOP_CHANCE` | braiding; fewer dead ends |
| `SPECIAL_PLAN` | material type, total, cluster size, latitude window |
| `ROOM_COUNT`, `GREEN_COUNT`, `ARTIFACT_COUNT`, `GLYPH_COUNT` | pickup budget |

Black-share levers, in order of usefulness: maze spacing, plazas, extra
branches/loops. Do not widen corridors past 3 by dilation radius 2 unless you
want 5-wide rooms; that eats the wall budget.

## Maze connectivity

- Build a node grid (spacing ~12–14 cells), spanning tree, braid ~18% of the
  extra edges, then **dilate the centreline by one hex ring** to get 3-wide
  corridors.
- Add black plazas at some southern/mid nodes for open fight space and to raise
  the black share.
- Validate connectivity by computing **all** layer-1 connected components and
  requiring one component. Do not test "can I reach the maze from the first
  entrance neighbour" — that can be a side-lobe.
- If a narrow appendage (the cow tail) has black cells, carve a corridor
  through it or it becomes a disconnected 79-cell island.

## Entrances that actually work

- Choose boundary cells on the planet side (max `r`); here, the four leg
  bottoms.
- **Use BFS through `cells` to connect the mouth to the maze.** A straight line
  between two points leaves the shape, skips cells, and produces a corridor
  that looks carved but is not connected.
- Cap the **full cross-section** at the mouth: the first two path cells plus
  their tunnel side cells, not just the centreline. Otherwise dilation leaves
  isolated black side-lobes behind the plug.
- Make the cap `alt`/layer **4 (gold)** and ensure the third cell inward is
  layer 1.
- Validate each entrance: on the boundary, layer 4, reachable L1 behind it, and
  in the main L1 component.
- Put the mouths at the lowest `r` pixels? No — planet side is **max r**.

## Layers and difficulty gradient

Use latitude `g = (r - rMin) / (rMax - rMin)` (0 = north/top, 1 = south/planet
side):

- **South** (early): layer 1 tunnels, **gold L4** and some **blue L2** walls;
  little pink/purple.
- **Middle**: blue/gold walls with some purple.
- **North**: **purple L5** and **pink L3** walls.

Observed COW ABDUCTION result:

- south tunnel walls 77% L4 / 20% L2; north tunnel walls 100% L3/L5
- mean mass HP 58 south → 82 mid → 113 north
- layer mix 28.2 / 10.6 / 16.1 / 21.2 / 23.9

Use **coherent patches** for deep mass layers. A per-cell hash makes
salt-and-pepper; a coarse block hash (5 cells) or low-frequency noise makes
readable bands. Keep wall decisions separate from deep-mass decisions.

Remember the HP order is non-monotonic: L1 15, **L4 40**, L2 60, L5 90,
**L3 160**. “Higher tier” in the request meant colour/tier, but pink is the
tankiest tile.

## Hidden rooms

- Target 7–19 cells, at least 4 cells from any tunnel so they do not leak into
  the maze.
- Rooms are tagged in `rooms.q/r/id`; breach happens when a neighbouring tile
  dies.
- For a “sealed section” in an otherwise easy southern area, wrap chosen rooms
  in a 2–3-cell L3/L5 shell. This is the exception to the gradient.
- Artifacts go inside rooms; one per room is a sensible default.

## Pickup budgets (important)

What the pickups actually are:

- **Artifacts (`meta_2`, `artifactCells`)** → one **power-up roll** each
  (`Boosters.AddFoundRoll`). Place them in rooms.
- **Glyphs (`glyphCount`)** → **beacons**; 3 beacons = 1 relic key, 20 relic
  slots. So a 2-player map wants **120 glyphs** (2 × 20 × 3).
- **Specials (`alt` 6–9)** → colour/material shards used for mod research.
  Author them in **clusters/veins**; do not scatter single cells.
- **Green (`roomGreen` / `greenCount`)** → salvage money crates. Set
  `greenCount` equal to the authored count (or higher if you want procedural
  extras, but they will be random).

Very important: **`SeedSpecials` runs before `PaintGreenShards`.** If a band
seeds a material on a green cell, that green cell fails to paint. Zero the band
`special*` counts if you author all veins. That is why COW ABDUCTION logs 64/64
crates instead of the earlier 33/36.

Reference frequency: ~12 artifacts, 58 glyphs, 166 specials, 40 crates per 25k
cells. Scale from that, then adjust to taste.

## Validation

Make the validator hard-fail on:

- count/bounds/parallel-array consistency and unique cells
- black share in the intended band (25–35%)
- one connected L1 component from all four entrances
- 3-wide: erode the tunnel set, regrow, require ≥95% coverage
- no layer-1 wall cells
- south wall mix ≥60% L2/L4, north ≥60% L3/L5
- south mean mass HP < north
- room count/sizes/distance, artifacts inside rooms
- `greenCount` matches authored greens and all are paintable
- `glyphCount >= 120` for a 2-player relic budget
- band `special*` counts are zero if you author veins
- specials are clustered, not in tunnels, and gold sits south of blue/green

Soft-report counts and warning; hard-fail on the design invariants so a
regression is obvious.

## Deployment and in-game checking

- The loader injects the contract from a `MainMenuController.BuildUI` postfix.
  **Never call `StructureCatalog.I` / `Resources.Load` from plugin `Awake`** —
  BepInEx loads plugins before Unity resources are ready and the game crashes.
- `loader/deploy.sh` copies the DLL + `maps/` + `contracts/` into
  `BepInEx/plugins/GraveyardOrbit.UfoCow/`.
- Restart the game after changing the map JSON; the contract is read at startup.
- Starting a **new** contract resets destruction; continuing an old `ufo_cow`
  save keeps old destroyed cells because `GameState.RecordDestroyed` persists.
- Log checks:
  - `[ufocow] injected 'ufo_cow' (50,221 cells, 5 bands)`
  - `[Megastructure] loaded 'ufo_cow' — 50221 cells`
  - `[MiningSortie] ... authored specials`, artifact/glyph/salvage counts
- Preview every iteration with `previews/ufo_cow.png`; it catches silhouettes
  and gradient mistakes faster than launching the game.

## Process shortcuts

- Keep the generator + validator + preview loop under a minute.
- Change one knob per regeneration; record the resulting counts in the commit
  or note.
- Keep the seed fixed for layout comparisons; change it only when you want a
  new maze.
- Keep the built DLL, map and contract hashes in sync when deploying.
- If a new map is a variant, copy this project's `generate_map.py`,
  `validate_map.py`, contract and loader; change ids and constants rather than
  starting from zero.
