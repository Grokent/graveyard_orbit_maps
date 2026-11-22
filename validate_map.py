#!/usr/bin/env python3
"""Validate maps/ufo_cow.json + contracts/ufo_cow.contract.json.

Format checks mirror MegastructureData.FromJson. Design checks cover the
requested layout: 25-35% layer 1, four gold-capped entrances from the planet
side, a south-to-north difficulty gradient, clustered mod materials, hidden
rooms, and enough beacons for two players.

Exit code is non-zero on a failed hard requirement.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP_PATH = ROOT / "maps" / "ufo_cow.json"
CONTRACT_PATH = ROOT / "contracts" / "ufo_cow.contract.json"

N6 = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
VALID_ALT = {0, 6, 7, 8, 9}
TARGET_CELLS = (49_000, 52_000)
LAYER_HP = {1: 15, 2: 60, 3: 160, 4: 40, 5: 90}

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def main() -> int:
    grid = json.loads(MAP_PATH.read_text())
    contract = json.loads(CONTRACT_PATH.read_text())

    q = grid.get("q") or []
    r = grid.get("r") or []
    alt = grid.get("alt") or []
    layer = grid.get("layer") or []
    count = grid.get("count")

    for name, arr in (("q", q), ("r", r), ("alt", alt), ("layer", layer)):
        if len(arr) != count:
            fail(f"array '{name}' length {len(arr)} != count {count}")
    if count != len(set(zip(q, r))):
        fail(f"count {count} != unique cells {len(set(zip(q, r)))}")
    if not TARGET_CELLS[0] <= count <= TARGET_CELLS[1]:
        fail(f"count {count} outside target {TARGET_CELLS}")
    if count != contract.get("cellCount"):
        fail(f"contract cellCount {contract.get('cellCount')} != map count {count}")

    cells = list(zip(q, r))
    cell_set = set(cells)
    layers = dict(zip(cells, layer))
    alts = dict(zip(cells, alt))

    if {v for v in layer if v not in (1, 2, 3, 4, 5)}:
        fail(f"invalid layers: {set(layer) - {1, 2, 3, 4, 5}}")
    if {v for v in alt if v not in VALID_ALT}:
        fail(f"invalid alt codes: {set(alt) - VALID_ALT}")
    want_bounds = {"q": [min(q), max(q)], "r": [min(r), max(r)]}
    if grid.get("bounds") != want_bounds:
        fail(f"bounds {grid.get('bounds')} != {want_bounds}")

    def neighbours(c):
        return [(c[0] + dq, c[1] + dr) for dq, dr in N6
                if (c[0] + dq, c[1] + dr) in cell_set]

    def flood(start, allowed):
        seen = {start}
        dq = collections.deque([start])
        while dq:
            u = dq.popleft()
            for v in neighbours(u):
                if v in allowed and v not in seen:
                    seen.add(v)
                    dq.append(v)
        return seen

    rs = [c[1] for c in cells]
    lo, hi = min(rs), max(rs)
    span = max(1, hi - lo)

    def lat(c):
        return (c[1] - lo) / span

    hist = collections.Counter(layer)
    total = len(cells)
    black_pct = 100 * hist[1] / total
    if not 25 <= black_pct <= 35:
        fail(f"layer-1 share {black_pct:.1f}% outside 25-35%")
    else:
        print(f"layer-1 share: {black_pct:.1f}% (target 25-35%)")

    # --- entrances ----------------------------------------------------------
    tunnels = {c for c in cells if layers[c] == 1}
    entrances = [tuple(e) for e in contract.get("entrances", [])]
    if len(entrances) < 4:
        fail(f"only {len(entrances)} entrances (need >=4)")
    for mouth in entrances:
        if mouth not in cell_set:
            fail(f"entrance {mouth} is not in the map")
            continue
        if layers[mouth] != 4:
            fail(f"entrance {mouth} is layer {layers[mouth]} (need L4 gold cap)")
        if not any((mouth[0] + dq, mouth[1] + dr) not in cell_set for dq, dr in N6):
            fail(f"entrance {mouth} is not on the boundary")
        if not any(layers[n] == 1 for n in neighbours(mouth)) and \
           not any(layers[n] == 1 for n in
                   {x for n in neighbours(mouth) for x in neighbours(n)}):
            fail(f"entrance {mouth} has no layer-1 tunnel behind the cap")
    print(f"entrances    : {len(entrances)} gold-capped")

    if tunnels:
        seen = set()
        comps = []
        for start in tunnels:
            if start in seen:
                continue
            comp = flood(start, tunnels)
            seen |= comp
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        if len(comps) > 1:
            fail(f"layer-1 network has {len(comps)} components "
                 f"(largest {len(comps[0])}, others {[len(c) for c in comps[1:5]]})")
        else:
            print(f"tunnel network: {len(tunnels)} cells, connected")
        main = set(comps[0])
        for mouth in entrances:
            near = {x for n in neighbours(mouth) for x in neighbours(n)} | set(neighbours(mouth))
            if not any(x in main for x in near if layers.get(x) == 1):
                fail(f"entrance {mouth} does not reach the main layer-1 network")

    # 3-wide (erode then regrow)
    interior = {c for c in tunnels if all(n in tunnels for n in neighbours(c))}
    if not interior:
        fail("no tunnel interior cells (network thinner than 3?)")
    regrown = set(interior)
    for c in interior:
        regrown.add(c)
        regrown.update(neighbours(c))
    coverage = len(tunnels & regrown) / max(1, len(tunnels))
    if coverage < 0.95:
        fail(f"tunnel 3-wide coverage only {coverage:.1%} (need >=95%)")
    else:
        print(f"tunnel width : 3-wide, coverage {coverage:.1%}")

    # --- gradient -----------------------------------------------------------
    walls = {n for c in tunnels for n in neighbours(c) if n not in tunnels}
    if not walls:
        fail("no wall cells")
    wall_bad = {c for c in walls if layers[c] == 1}
    if wall_bad:
        fail(f"{len(wall_bad)} wall cells are layer 1")

    def thirds(selector):
        buckets = {"north": [], "mid": [], "south": []}
        for c in selector:
            g = lat(c)
            buckets["north" if g < 1 / 3 else ("mid" if g < 2 / 3 else "south")].append(c)
        return buckets

    wall_buckets = thirds(walls)
    for name in ("north", "mid", "south"):
        h = collections.Counter(layers[c] for c in wall_buckets[name])
        n = max(1, sum(h.values()))
        pct = {k: round(100 * v / n, 1) for k, v in sorted(h.items())}
        print(f"walls {name:5s}: {pct}")

    south_walls = collections.Counter(layers[c] for c in wall_buckets["south"])
    north_walls = collections.Counter(layers[c] for c in wall_buckets["north"])
    n_south = max(1, sum(south_walls.values()))
    n_north = max(1, sum(north_walls.values()))
    south_easy = (south_walls[2] + south_walls[4]) / n_south
    north_hard = (north_walls[3] + north_walls[5]) / n_north
    if south_easy < 0.60:
        fail(f"south walls only {south_easy:.0%} blue/gold (need >=60%)")
    if north_hard < 0.60:
        fail(f"north walls only {north_hard:.0%} pink/purple (need >=60%)")
    print(f"gradient     : south walls {south_easy:.0%} L2/L4, "
          f"north walls {north_hard:.0%} L3/L5")

    mass = [c for c in cells if layers[c] != 1]
    by_third = thirds(mass)
    mean_hp = {}
    for name, cs in by_third.items():
        mean_hp[name] = sum(LAYER_HP[layers[c]] for c in cs) / max(1, len(cs))
    print("mean mass HP : " + "  ".join(
        f"{k}={v:.0f}" for k, v in mean_hp.items()))
    if mean_hp["south"] >= mean_hp["north"]:
        fail(f"south mass HP {mean_hp['south']:.0f} is not below north "
             f"{mean_hp['north']:.0f}")

    # --- rooms / green / artifacts -----------------------------------------
    rooms = grid.get("rooms") or {}
    rq, rr, rid = rooms.get("q", []), rooms.get("r", []), rooms.get("id", [])
    if not (len(rq) == len(rr) == len(rid)):
        fail("rooms arrays have different lengths")
    room_cells = collections.defaultdict(set)
    for a, b, room in zip(rq, rr, rid):
        c = (a, b)
        if c not in cell_set:
            fail(f"room {room} cell {c} not in the map")
        room_cells[room].add(c)
        if layers[c] == 1:
            fail(f"room {room} cell {c} is a layer-1 tunnel")
    sizes = [len(v) for v in room_cells.values()]
    if not room_cells:
        fail("no hidden rooms")
    elif not (7 <= min(sizes) and max(sizes) <= 19):
        fail(f"room size range {min(sizes)}-{max(sizes)} outside 7-19")
    if len(room_cells) < 20:
        fail(f"only {len(room_cells)} hidden rooms (need >=20)")

    dist = {c: 0 for c in tunnels}
    dq = collections.deque(tunnels)
    while dq:
        c = dq.popleft()
        for n in neighbours(c):
            if n not in dist:
                dist[n] = dist[c] + 1
                dq.append(n)
    min_room_dist = min(dist.get(c, 999) for v in room_cells.values() for c in v)
    if min_room_dist < 3:
        fail(f"a hidden room is only {min_room_dist} cells from a tunnel")
    print(f"hidden rooms : {len(room_cells)} rooms, {min(sizes)}-{max(sizes)} cells, "
          f">= {min_room_dist} cells from tunnels")

    greens = list(zip((grid.get("roomGreen") or {}).get("q", []),
                      (grid.get("roomGreen") or {}).get("r", [])))
    if len(greens) != contract.get("greenCount"):
        fail(f"greenCount {contract.get('greenCount')} != authored {len(greens)}")
    if len(greens) < 56:
        fail(f"only {len(greens)} green shards (need >=56)")
    for c in greens:
        if c not in cell_set:
            fail(f"green shard {c} is not in the map")
        if layers[c] == 1:
            fail(f"green shard {c} sits in a tunnel")

    artifacts = [tuple(c) for c in contract.get("artifactCells", [])]
    if len(artifacts) < 16:
        fail(f"only {len(artifacts)} artifacts (need >=16 for power-up rolls)")
    room_set = {x for v in room_cells.values() for x in v}
    for c in artifacts:
        if c not in cell_set:
            fail(f"artifact {c} is not in the map")
        if layers[c] == 1:
            fail(f"artifact {c} sits in a tunnel")
        if c not in room_set:
            fail(f"artifact {c} is not inside a hidden room")

    glyphs = contract.get("glyphCount", 0)
    if glyphs < 120:
        fail(f"glyphCount {glyphs} < 120 (2 players x 20 relics x 3 beacons)")
    else:
        print(f"beacons      : {glyphs} glyphs "
              f"(enough for 2 players x 20 relics)")

    # --- material/mod tiles -------------------------------------------------
    bands = {b.get("layer"): b for b in contract.get("bands", [])}
    missing = [l for l in range(1, 6) if l not in bands]
    if missing:
        fail(f"contract is missing bands for layers {missing}")
    for l, band in bands.items():
        for key in ("special1", "special2", "special3", "meta1"):
            if band.get(key, 0) != 0:
                fail(f"band {l} still seeds procedural {key} "
                     f"({band.get(key)}); authored veins are the design")

    specials = {c: a for c, a in alts.items() if a}
    if not 250 <= len(specials) <= 340:
        fail(f"{len(specials)} authored specials outside 250-340")
    for c in specials:
        if layers[c] == 1:
            fail(f"special {c} sits in a tunnel")
    names = {6: "gold", 7: "red", 8: "blue", 9: "green"}
    lats = {}
    for code in (6, 7, 8, 9):
        cs = [c for c, a in specials.items() if a == code]
        if not cs:
            fail(f"no {names[code]} specials")
            continue
        lats[code] = sum(lat(c) for c in cs) / len(cs)
        clustered = sum(1 for c in cs if any(alts[n] == code for n in neighbours(c)))
        print(f"special {names[code]:5s}: {len(cs):3d}  mean latitude {lats[code]:.2f}  "
              f"clustered {100 * clustered / len(cs):.0f}%")
    if lats.get(6, 0) <= lats.get(8, 1):
        fail("gold specials are not south of blue specials")
    if lats.get(6, 0) <= lats.get(9, 1):
        fail("gold specials are not south of green specials")

    # --- summary ------------------------------------------------------------
    print()
    for l in sorted(hist):
        print(f"  layer {l} : {hist[l]:6d}  {100 * hist[l] / total:5.1f}%")
    for w in warnings:
        print(f"warn: {w}")
    if errors:
        print()
        for e in errors:
            print(f"FAIL: {e}")
        return 1
    print("\nOK: format, 25-35% black, 4 gold entrances, connected 3-wide maze, "
          "south-to-north gradient, clustered mod tiles, rooms, beacons.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
