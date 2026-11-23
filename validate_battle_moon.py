#!/usr/bin/env python3
"""Validate maps/battle_moon.json + contracts/battle_moon.contract.json.

Format checks mirror MegastructureData.FromJson. Design checks cover the
requested station: a 3/4 view from below-right, NO labyrinth (the trench is
the only layer-1 space), a black 7-cell equatorial trench capped at both rims,
two gold-capped trench mouths, eight panelled meridian sectors with a
south-to-north material gradient, and a superlaser dish low and left of centre
(gold rim, blue basin, pink core).

Dish and view geometry is derived from the generator's constants and the map's
own radius, so it follows the default --scale.

Exit code is non-zero on a failed hard requirement.
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP_PATH = ROOT / "maps" / "battle_moon.json"
CONTRACT_PATH = ROOT / "contracts" / "battle_moon.contract.json"

N6 = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
VALID_ALT = {0, 6, 7, 8, 9}
TARGET_CELLS = (58_000, 62_000)
LAYER_HP = {1: 15, 2: 60, 3: 160, 4: 40, 5: 90}

DISC_R = 138.0
CAM_LAT = -10.0
CAM_LON = 20.0
DISH_LAT = 22.0
DISH_LON = -5.0
DISH_ANG = 15.0
DISH_CORE = 3.5
DISH_BASIN = (4.4, 12.4)
DISH_RIM = (12.4, 14.9)
DISH_HALO = 16.2
TRENCH_LAT = 2.2
RING_NORTH = 20.0
RING_SOUTH = -30.0
SECTOR_COUNT = 8

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def _rad(d):
    return math.radians(d)


def _clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def _norm(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / n, v[1] / n, v[2] / n)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sph(lat, lon):
    return (math.cos(_rad(lat)) * math.sin(_rad(lon)),
            math.sin(_rad(lat)),
            math.cos(_rad(lat)) * math.cos(_rad(lon)))


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

    def px(c):
        return c[0] + c[1] * 0.5

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

    radius = max(abs(min(c[1] for c in cells)), abs(max(c[1] for c in cells)))
    s = radius / DISC_R

    # same orthographic sphere as the generator
    fwd = sph(CAM_LAT, CAM_LON)
    right = _norm(_cross((0.0, 1.0, 0.0), fwd))
    up = _cross(fwd, right)
    dish_v = sph(DISH_LAT, DISH_LON)
    dish_east = (math.cos(_rad(DISH_LON)), 0.0, -math.sin(_rad(DISH_LON)))
    dish_north = _cross(dish_v, dish_east)

    lat_of, lon_of, dish_ang, dish_u, dish_vv = {}, {}, {}, {}, {}
    for c in cells:
        u = px(c) / radius
        v = -c[1] / radius
        w = math.sqrt(max(0.0, 1.0 - u * u - v * v))
        p = (u * right[0] + v * up[0] + w * fwd[0],
             u * right[1] + v * up[1] + w * fwd[1],
             u * right[2] + v * up[2] + w * fwd[2])
        lat_of[c] = math.degrees(math.asin(_clamp(p[1])))
        lon_of[c] = math.degrees(math.atan2(p[0], p[2]))
        cosang = _clamp(_dot(p, dish_v))
        dish_ang[c] = math.degrees(math.acos(cosang))
        dish_u[c] = u
        dish_vv[c] = v

    hist = collections.Counter(layer)
    total = len(cells)
    black_pct = 100 * hist[1] / total
    if not 30.0 <= black_pct <= 36.0:
        fail(f"layer-1 share {black_pct:.1f}% outside 30-36% "
             f"(panel grout + open panels + trench)")
    else:
        print(f"layer-1 share: {black_pct:.1f}% (target 30-36%)")

    # --- trench and "no maze" ------------------------------------------------
    trench = {c for c in cells if abs(lat_of[c]) <= TRENCH_LAT}
    trench_black = {c for c in trench if layers[c] == 1}
    if not trench:
        fail("no equatorial trench cells")
    else:
        share = len(trench_black) / len(trench)
        t_minx = min(px(c) for c in trench)
        t_maxx = max(px(c) for c in trench)
        g_minx = min(px(c) for c in cells)
        g_maxx = max(px(c) for c in cells)
        if share < 0.90:
            fail(f"trench is only {share:.1%} layer 1 (need >=90%)")
        if t_minx > g_minx + 2 or t_maxx < g_maxx - 2:
            fail("trench does not run limb to limb")
        print(f"trench       : {len(trench)} cells, {share:.1%} black, "
              f"spans {t_minx:.0f}..{t_maxx:.0f}")

    tunnels = {c for c in cells if layers[c] == 1}

    def bdist(v, period):
        m = v % period
        return min(m, period - m)

    grid_black = 0
    for c in tunnels:
        lat = lat_of[c]
        rel = ((lon_of[c] - CAM_LON + 180.0) % 360.0) - 180.0
        near_lat = bdist(lat, 10.0) < 0.8
        near_lon = (bdist(rel + 90.0, 11.25)
                    * max(math.cos(_rad(lat)), 0.30)) < 0.8
        if abs(lat) <= TRENCH_LAT + 0.5 or near_lat or near_lon:
            grid_black += 1
    grid_share = grid_black / max(1, len(tunnels))
    if grid_share < 0.55:
        fail(f"only {grid_share:.0%} of black is panel grout or trench "
             f"(need >=55%)")
    else:
        print(f"black layout : {grid_share:.0%} grout/trench, "
              f"{100 - 100 * grid_share:.0f}% open panel bays")

    # --- entrances ----------------------------------------------------------
    def l1_within(mouth, radius=5):
        seen = {mouth}
        frontier = {mouth}
        for _ in range(radius):
            nxt = set()
            for u in frontier:
                for v in neighbours(u):
                    if v not in seen:
                        seen.add(v)
                        nxt.add(v)
            frontier = nxt
        return {c for c in seen if layers.get(c) == 1}

    # The trench is tangent to the limb, so the black band curves away from the
    # mouth; the first black cell sits up to five hex steps behind the cap.
    entrances = [tuple(e) for e in contract.get("entrances", [])]
    if len(entrances) < 2:
        fail(f"only {len(entrances)} entrances (need >=2)")
    for mouth in entrances:
        if mouth not in cell_set:
            fail(f"entrance {mouth} is not in the map")
            continue
        if layers[mouth] != 4:
            fail(f"entrance {mouth} is layer {layers[mouth]} (need L4 gold cap)")
        if not any((mouth[0] + dq, mouth[1] + dr) not in cell_set for dq, dr in N6):
            fail(f"entrance {mouth} is not on the boundary")
        if not l1_within(mouth):
            fail(f"entrance {mouth} has no layer-1 trench behind the cap")
    print(f"entrances    : {len(entrances)} gold-capped trench mouths")

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
        main_net = set(comps[0])
        for mouth in entrances:
            if not (l1_within(mouth) & main_net):
                fail(f"entrance {mouth} does not reach the main layer-1 network")

    # --- gradient and sector panelling --------------------------------------
    walls = {n for c in tunnels for n in neighbours(c) if n not in tunnels}
    if not walls:
        fail("no wall cells")
    wall_bad = {c for c in walls if layers[c] == 1}
    if wall_bad:
        fail(f"{len(wall_bad)} wall cells are layer 1")

    def sector_of(c):
        rel = ((lon_of[c] - CAM_LON + 180.0) % 360.0) - 180.0
        return max(0, min(SECTOR_COUNT - 1,
                          int((rel + 90.0) / (180.0 / SECTOR_COUNT))))

    def third_of(c):
        if lat_of[c] > RING_NORTH:
            return "north"
        if lat_of[c] < RING_SOUTH:
            return "south"
        return "mid"

    mass = [c for c in cells
            if layers[c] != 1 and dish_ang[c] > DISH_HALO + 0.5]
    buckets = collections.defaultdict(collections.Counter)
    for c in mass:
        buckets[(sector_of(c), third_of(c))][layers[c]] += 1

    south_tot = collections.Counter()
    north_tot = collections.Counter()
    for (sec, ring), h in buckets.items():
        if ring == "south":
            south_tot.update(h)
        elif ring == "north":
            north_tot.update(h)
    n_south = max(1, sum(south_tot.values()))
    n_north = max(1, sum(north_tot.values()))
    south_easy = (south_tot[2] + south_tot[4]) / n_south
    north_hard = (north_tot[3] + north_tot[5]) / n_north
    if south_easy < 0.60:
        fail(f"underside is only {south_easy:.0%} blue/gold (need >=60%)")
    if north_hard < 0.60:
        fail(f"north hull is only {north_hard:.0%} pink/purple (need >=60%)")
    print(f"gradient     : underside {south_easy:.0%} L2/L4, "
          f"north {north_hard:.0%} L3/L5")

    mean_hp = {
        "south": sum(LAYER_HP[layers[c]] for c in mass
                     if third_of(c) == "south") / max(1, n_south),
        "north": sum(LAYER_HP[layers[c]] for c in mass
                     if third_of(c) == "north") / max(1, n_north),
    }
    if mean_hp["south"] >= mean_hp["north"]:
        fail(f"underside mass HP {mean_hp['south']:.0f} is not below north "
             f"{mean_hp['north']:.0f}")

    checked = 0
    for sec in range(SECTOR_COUNT):
        south = buckets[(sec, "south")]
        north = buckets[(sec, "north")]
        ns, nn = sum(south.values()), sum(north.values())
        ok = 0
        if ns >= 40:
            easy = (south[2] + south[4]) / ns
            if easy < 0.55:
                fail(f"sector {sec} underside is only {easy:.0%} L2/L4")
            else:
                ok += 1
        else:
            warn(f"sector {sec} underside has only {ns} cells; skipped")
        if nn >= 40:
            hard = (north[3] + north[5]) / nn
            if hard < 0.55:
                fail(f"sector {sec} north is only {hard:.0%} L3/L5")
            else:
                ok += 1
        else:
            warn(f"sector {sec} north has only {nn} cells; skipped")
        if ok == 2:
            checked += 1
        print(f"  sector {sec}: underside {100 * south[4] / max(1, ns):4.0f}% gold / "
              f"{100 * south[2] / max(1, ns):4.0f}% blue ({ns:4d})   "
              f"north {100 * north[3] / max(1, nn):4.0f}% pink / "
              f"{100 * north[5] / max(1, nn):4.0f}% purple ({nn:4d})")
    if checked < 6:
        fail(f"only {checked}/{SECTOR_COUNT} sectors fully checked "
             f"(need >=6 with 40+ cells per ring)")
    for k in (2, 4):
        if south_tot[k] / n_south < 0.10:
            fail(f"L{k} is only {100 * south_tot[k] / n_south:.0f}% of the "
                 f"underside (need both L2 and L4)")
    for k in (3, 5):
        if north_tot[k] / n_north < 0.10:
            fail(f"L{k} is only {100 * north_tot[k] / n_north:.0f}% of the "
                 f"north hull (need both L3 and L5)")

    # --- superlaser dish ----------------------------------------------------
    dish = [c for c in cells if dish_ang[c] <= DISH_ANG]
    if len(dish) < 2500:
        fail(f"dish region has only {len(dish)} cells (need >=2500)")
    cu = sum(dish_u[c] for c in dish) / max(1, len(dish))
    cv = sum(dish_vv[c] for c in dish) / max(1, len(dish))
    if cu > -0.12:
        fail(f"dish centroid x={cu:+.2f}; it should sit left of centre")
    if cv < 0.20:
        fail(f"dish centroid y={cv:+.2f}; it should sit north of the equator")
    if len(dish) >= 2500:
        print(f"dish         : {len(dish)} cells, centroid ({cu:+.2f}, {cv:+.2f})")

    def share_of(selector, want):
        n = len(selector)
        if not n:
            return 0.0, 0
        return sum(1 for c in selector if layers[c] == want) / n, n

    core = [c for c in dish if dish_ang[c] <= DISH_CORE]
    basin = [c for c in dish if DISH_BASIN[0] <= dish_ang[c] <= DISH_BASIN[1]]
    rim = [c for c in dish if DISH_RIM[0] <= dish_ang[c] <= DISH_RIM[1]]
    core_pink, n_core = share_of(core, 3)
    basin_blue, n_basin = share_of(basin, 2)
    rim_gold, n_rim = share_of(rim, 4)
    if core_pink < 0.55:
        fail(f"dish core is only {core_pink:.0%} pink (need >=55%)")
    if basin_blue < 0.55:
        fail(f"dish basin is only {basin_blue:.0%} blue (need >=55%)")
    if rim_gold < 0.60:
        fail(f"dish rim is only {rim_gold:.0%} gold (need >=60%)")
    print(f"dish layers  : core {core_pink:.0%} pink, basin {basin_blue:.0%} blue, "
          f"rim {rim_gold:.0%} gold")

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
            fail(f"room {room} cell {c} is a layer-1 trench cell")
    sizes = [len(v) for v in room_cells.values()]
    if not room_cells:
        fail("no hidden rooms")
    elif not (7 <= min(sizes) and max(sizes) <= 19):
        fail(f"room size range {min(sizes)}-{max(sizes)} outside 7-19")
    if len(room_cells) < 28:
        fail(f"only {len(room_cells)} hidden rooms (need >=28)")

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
        fail(f"a hidden room is only {min_room_dist} cells from the trench")
    print(f"hidden rooms : {len(room_cells)} rooms, {min(sizes)}-{max(sizes)} cells, "
          f">= {min_room_dist} cells from the trench")

    greens = list(zip((grid.get("roomGreen") or {}).get("q", []),
                      (grid.get("roomGreen") or {}).get("r", [])))
    if len(greens) != contract.get("greenCount"):
        fail(f"greenCount {contract.get('greenCount')} != authored {len(greens)}")
    if len(greens) < 88:
        fail(f"only {len(greens)} green shards (need >=88)")
    for c in greens:
        if c not in cell_set:
            fail(f"green shard {c} is not in the map")
        if layers[c] == 1:
            fail(f"green shard {c} sits in the trench")

    artifacts = [tuple(c) for c in contract.get("artifactCells", [])]
    if len(artifacts) < 26:
        fail(f"only {len(artifacts)} artifacts (need >=26 for power-up rolls)")
    room_set = {x for v in room_cells.values() for x in v}
    for c in artifacts:
        if c not in cell_set:
            fail(f"artifact {c} is not in the map")
        if layers[c] == 1:
            fail(f"artifact {c} sits in the trench")
        if c not in room_set:
            fail(f"artifact {c} is not inside a hidden room")

    glyphs = contract.get("glyphCount", 0)
    if glyphs < 120:
        fail(f"glyphCount {glyphs} < 120 (2 players x 20 relics x 3 beacons)")
    else:
        print(f"beacons      : {glyphs} glyphs "
              f"(enough for 2 players x 20 relics)")

    money = contract.get("startingMoney")
    if money != 1000:
        fail(f"startingMoney {money} != 1000")
    else:
        print(f"starting money: ${money}")

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
    if not 360 <= len(specials) <= 440:
        fail(f"{len(specials)} authored specials outside 360-440")
    for c in specials:
        if layers[c] == 1:
            fail(f"special {c} sits in the trench")
    names = {6: "gold", 7: "red", 8: "blue", 9: "green"}
    gmeans = {}
    for code in (6, 7, 8, 9):
        cs = [c for c, a in specials.items() if a == code]
        if not cs:
            fail(f"no {names[code]} specials")
            continue
        gmeans[code] = sum((c[1] - min(rr0 for rr0 in r))
                           / max(1, max(r) - min(r)) for c in cs) / len(cs)
        clustered = sum(1 for c in cs if any(alts[n] == code for n in neighbours(c)))
        print(f"special {names[code]:5s}: {len(cs):3d}  mean screen y {gmeans[code]:.2f}  "
              f"clustered {100 * clustered / len(cs):.0f}%")
    if gmeans.get(6, 0) <= gmeans.get(8, 1):
        fail("gold specials are not below blue specials on screen")
    if gmeans.get(6, 0) <= gmeans.get(9, 1):
        fail("gold specials are not below green specials on screen")

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
    print("\nOK: format, 30%+ black grout/open bays, wide black trench, 2 gold "
          "mouths, 3/4 view, northern left-of-centre dish, 8 sectors, rooms, "
          "beacons, $1000 start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
