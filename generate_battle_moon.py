#!/usr/bin/env python3
"""Generate the BATTLE MOON contract map for Graveyard Orbit.

Design:
  * a planet-killer battlestation seen in 3/4 view from below-right: the
    surface is projected off a unit sphere, so the meridians converge at the
    visible south pole and the equator arcs across the upper half;
  * NO labyrinth. The only layer-1 space is the equatorial trench plus two
    short docking shafts;
  * a 7-cell black trench band running limb to limb, capped in gold at both
    rims, with two gold-capped southern docking bays (4 entrances total);
  * a superlaser dish on the visible underside, left of centre and
    foreshortened: gold rim, blue basin with gold ribs and a groove, pink
    emitter core, hidden focus chamber;
  * eight meridian hull sectors x three latitude rings, each sector with its
    own wall palette, so the panelling changes across the station;
  * authored material veins only (no procedural confetti);
  * reference-scaled pickups: 29 artifacts, 140 glyphs, 96 crates, 399
    specials, 32 hidden rooms, starting money $1000.

Outputs: maps/battle_moon.json, contracts/battle_moon.contract.json,
previews/battle_moon.png
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP_ID = "battle_moon"
MAP_NAME = "BATTLE MOON"
MAP_DESC = ("A planet-killer battlestation seen from below-right: black panel "
            "grout and open bays around a wide equatorial trench, a superlaser "
            "dish north of the equator and left of centre, and eight panelled "
            "hull sectors. Two gold-capped trench mouths are the only openings.")

DEFAULT_SEED = 0xB47713
DEFAULT_SCALE = 1.0

DISC_R = 138.0

# camera in station coordinates: below the equator, right of the dish meridian
CAM_LAT = -10.0
CAM_LON = 20.0

# superlaser dish: northern hemisphere, west of the sub-camera meridian
DISH_LAT = 22.0
DISH_LON = -5.0
DISH_ANG = 15.0
DISH_CORE = 3.5
DISH_CORE_RING = 4.4
DISH_RIM_IN = 12.4
DISH_HALO = 16.2

TRENCH_LAT = 2.2                 # ~10 cells wide at the sub-camera meridian
LIP_LAT = 3.7                    # 2-cell gold lip each side
RING_NORTH = 20.0                # latitude ring boundaries, on the 10 grid
RING_SOUTH = -30.0

PANEL_LAT = 10.0                 # hull panels: 10 deg latitude x 11.25 lon
PANEL_LON = 11.25                # two panels per 22.5 deg sector
GAP_HALF = 0.55                  # half-width of the black grout, degrees
BAY_FULL = 8                     # % of panels opened completely
BAY_HALF = 16                    # % of panels with a half-open recess

ROOM_COUNT = 31                  # + 1 focus chamber = 32 rooms
ROOM_MIN, ROOM_MAX = 7, 19
GREEN_COUNT = 96
ARTIFACT_COUNT = 29
GLYPH_COUNT = 140                # 2 players x 20 relics x 3 beacons = 120+

# alt code, total cells, cluster size, latitude window (0=north, 1=south)
SPECIAL_PLAN = (
    (6, 150, (2, 4), (0.50, 1.00), False),  # special_1 gold, underside
    (7, 120, (2, 3), (0.35, 0.90), False),  # special_2 red, mid
    (8, 80, (2, 3), (0.10, 0.60), False),   # special_3 blue, upper hull
    (9, 50, (1, 2), (0.00, 0.45), True),    # meta_1 green, north + rooms
)

N6 = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))
LAYER_RGB = {
    1: (20, 20, 25),
    2: (58, 107, 255),
    3: (237, 23, 81),
    4: (245, 130, 33),
    5: (123, 63, 176),
}
HP = {1: 15, 2: 60, 3: 160, 4: 40, 5: 90}

# Eight meridian sectors (0 = west limb, 7 = east limb), each with a
# south/mid/north palette. South stays blue/gold, north pink/purple; the
# proportions change from sector to sector.
PALETTES = (
    {  # 0 west limb: gold-heavy underside, purple north
        "south": {4: 70, 2: 30},
        "mid": {5: 45, 4: 30, 2: 25},
        "north": {5: 65, 3: 35},
    },
    {  # 1 west
        "south": {2: 70, 4: 30},
        "mid": {4: 45, 5: 30, 2: 25},
        "north": {3: 65, 5: 35},
    },
    {  # 2 inner west
        "south": {4: 60, 2: 40},
        "mid": {5: 50, 2: 25, 4: 25},
        "north": {3: 60, 5: 40},
    },
    {  # 3 centre west
        "south": {2: 65, 4: 35},
        "mid": {2: 45, 5: 30, 4: 25},
        "north": {5: 60, 3: 40},
    },
    {  # 4 centre east: gold south, pink north
        "south": {4: 65, 2: 35},
        "mid": {2: 50, 4: 30, 5: 20},
        "north": {3: 55, 5: 45},
    },
    {  # 5 inner east
        "south": {2: 60, 4: 40},
        "mid": {4: 50, 2: 30, 5: 20},
        "north": {5: 55, 3: 45},
    },
    {  # 6 east: very gold underside
        "south": {4: 75, 2: 25},
        "mid": {2: 50, 4: 30, 5: 20},
        "north": {3: 60, 5: 40},
    },
    {  # 7 east limb
        "south": {2: 75, 4: 25},
        "mid": {2: 45, 5: 35, 4: 20},
        "north": {5: 60, 3: 40},
    },
)


# --------------------------------------------------------------------- helpers
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
    return (_rad(0) + math.cos(_rad(lat)) * math.sin(_rad(lon)),
            math.sin(_rad(lat)),
            math.cos(_rad(lat)) * math.cos(_rad(lon)))


def axial_cell(px, py):
    r = round(py)
    return round(px - r * 0.5), r


def hex_distance(a, b):
    dq, dr = a[0] - b[0], a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def _hash(cell, salt, seed):
    x = (cell[0] * 73856093) ^ (cell[1] * 19349663) ^ (salt * 83492791) ^ seed
    x = (x ^ (x >> 13)) * 1274126177
    return (x ^ (x >> 16)) & 0xFFFFFFFF


# ------------------------------------------------------------------ generator
def build(scale: float, seed: int) -> dict:
    rng = random.Random(seed)
    r_px = DISC_R * scale

    # view basis (orthographic sphere, camera at CAM_LAT/CAM_LON)
    fwd = sph(CAM_LAT, CAM_LON)
    right = _norm(_cross((0.0, 1.0, 0.0), fwd))
    up = _cross(fwd, right)

    dish_v = sph(DISH_LAT, DISH_LON)
    dish_east = (math.cos(_rad(DISH_LON)), 0.0, -math.sin(_rad(DISH_LON)))
    dish_north = _cross(dish_v, dish_east)

    # solid sphere ------------------------------------------------------------
    cells = set()
    lat_of = {}
    lon_of = {}
    lim = int(DISC_R / scale) + 4
    for r in range(-lim, lim + 1):
        for q in range(-2 * lim, 2 * lim + 1):
            px, py = q + r * 0.5, r
            u = px / r_px
            v = -py / r_px
            d2 = u * u + v * v
            if d2 > 1.0:
                continue
            w = math.sqrt(max(0.0, 1.0 - d2))
            p = (u * right[0] + v * up[0] + w * fwd[0],
                 u * right[1] + v * up[1] + w * fwd[1],
                 u * right[2] + v * up[2] + w * fwd[2])
            cells.add((q, r))
            lat_of[(q, r)] = math.degrees(math.asin(_clamp(p[1])))
            lon_of[(q, r)] = math.degrees(math.atan2(p[0], p[2]))
    if not cells:
        raise SystemExit("empty shape")

    min_py = min(c[1] for c in cells)
    max_py = max(c[1] for c in cells)

    def gnorm(c):
        return (c[1] - min_py) / max(1, max_py - min_py)  # 0 north, 1 south

    def screen(c):
        return c[0] + c[1] * 0.5, c[1]

    def neighbours(c):
        q, r = c
        return [(q + dq, r + dr) for dq, dr in N6 if (q + dq, r + dr) in cells]

    def dish_geom(c):
        """Angular distance from the dish centre and local azimuth (deg)."""
        px, py = screen(c)
        u = px / r_px
        v = -py / r_px
        w = math.sqrt(max(0.0, 1.0 - u * u - v * v))
        p = (u * right[0] + v * up[0] + w * fwd[0],
             u * right[1] + v * up[1] + w * fwd[1],
             u * right[2] + v * up[2] + w * fwd[2])
        cosang = _clamp(_dot(p, dish_v))
        ang = math.degrees(math.acos(cosang))
        tang = (p[0] - dish_v[0] * cosang,
                p[1] - dish_v[1] * cosang,
                p[2] - dish_v[2] * cosang)
        az = math.degrees(math.atan2(_dot(tang, dish_north),
                                     _dot(tang, dish_east)))
        return ang, az

    # shell depth -------------------------------------------------------------
    outside_dist = {}
    queue = collections.deque()
    for c in cells:
        if any((c[0] + dq, c[1] + dr) not in cells for dq, dr in N6):
            outside_dist[c] = 1
            queue.append(c)
    while queue:
        c = queue.popleft()
        d = outside_dist[c] + 1
        for n in neighbours(c):
            if n not in outside_dist:
                outside_dist[n] = d
                queue.append(n)

    # the trench is the only long layer-1 space ------------------------------
    trench = {c for c in cells if abs(lat_of[c]) <= TRENCH_LAT}
    lips = {c for c in cells if TRENCH_LAT < abs(lat_of[c]) <= LIP_LAT}
    dish_cells = {c for c in cells if dish_geom(c)[0] <= DISH_ANG + 1.0}

    # gold caps: two outer slices of the trench, one mouth at each limb ------
    caps = set()
    trench_px = sorted(screen(c)[0] for c in trench)
    if trench_px:
        cap_w, cap_e = trench_px[0] + 1.6, trench_px[-1] - 1.6
        for c in trench:
            x = screen(c)[0]
            if x <= cap_w or x >= cap_e:
                caps.add(c)

    # layer assignment -------------------------------------------------------
    def patch_roll(c, salt, block):
        px, py = screen(c)
        key = (int(math.floor(px / block)), int(math.floor(py / block)))
        return _hash(key, salt, seed) % 100

    def lon_rel(c):
        return ((lon_of[c] - CAM_LON + 180.0) % 360.0) - 180.0

    def sector_of(c):
        return max(0, min(7, int((lon_rel(c) + 90.0) / 22.5)))

    def ring_of(c):
        lat = lat_of[c]
        if lat > RING_NORTH:
            return "north"
        if lat < RING_SOUTH:
            return "south"
        return "mid"

    def pick(weights, r100):
        total = sum(weights.values())
        x = r100 * total / 100.0
        acc = 0
        for layer in sorted(weights):
            acc += weights[layer]
            if x < acc:
                return layer
        return max(weights)

    def boundary_dist(v, period):
        m = v % period
        return min(m, period - m)

    def panel_key(c):
        return (int(math.floor(lat_of[c] / PANEL_LAT)),
                int(math.floor((lon_rel(c) + 90.0) / PANEL_LON)))

    def is_gap(c):
        """Black grout on the hull-panel boundaries."""
        lat = lat_of[c]
        if boundary_dist(lat, PANEL_LAT) < GAP_HALF:
            return True
        dlon = boundary_dist(lon_rel(c) + 90.0, PANEL_LON)
        return dlon * max(math.cos(_rad(lat)), 0.30) < GAP_HALF

    def bay_kind(c):
        """0 = plated panel, 1 = half-open recess, 2 = open bay."""
        h = _hash(panel_key(c), 41, seed) % 100
        if h < BAY_FULL:
            return 2
        if h < BAY_HALF:
            local = (lon_rel(c) + 90.0) % PANEL_LON
            return 1 if local < PANEL_LON * 0.5 else 0
        return 0

    def palette_layer(c):
        # one solid layer per 10 x 11.25 degree hull panel
        return pick(PALETTES[sector_of(c)][ring_of(c)],
                    _hash(panel_key(c), 23, seed) % 100)

    def dish_layer(c, ang, az):
        if ang <= DISH_CORE:
            return 3
        if ang <= DISH_CORE_RING:
            return 4
        if ang <= DISH_RIM_IN:
            rib = (ang * math.sin(_rad(min(az % 45.0, 45.0 - az % 45.0)))
                   < 0.70)
            groove = abs(ang - 9.8) < 0.50
            return 4 if (rib or groove) else 2
        return 4

    solid_dish = {c for c in cells if dish_geom(c)[0] <= DISH_HALO + 0.5}
    gap_cells = set()
    bay_cells = set()
    for c in cells:
        if c in caps or c in trench or c in solid_dish:
            continue
        if is_gap(c):
            gap_cells.add(c)
        elif bay_kind(c):
            bay_cells.add(c)

    layers = {}
    for c in cells:
        ang, az = dish_geom(c)
        if c in caps:
            layers[c] = 4
        elif ang <= DISH_ANG:
            layers[c] = dish_layer(c, ang, az)
        elif ang <= DISH_HALO:
            layers[c] = 5
        elif c in trench:
            layers[c] = 1
        elif c in gap_cells or c in bay_cells:
            layers[c] = 1
        elif c in lips:
            layers[c] = 4
        else:
            layers[c] = palette_layer(c)

    # prune isolated black fragments where the grout converges at the poles
    open_cells = {c for c in layers if layers[c] == 1}
    seen_open = set()
    open_comps = []
    for c in open_cells:
        if c in seen_open:
            continue
        comp = {c}
        stack = [c]
        seen_open.add(c)
        while stack:
            u = stack.pop()
            for n in neighbours(u):
                if n in open_cells and n not in seen_open:
                    seen_open.add(n)
                    comp.add(n)
                    stack.append(n)
        open_comps.append(comp)
    main_open = max(open_comps, key=len) if open_comps else set()
    for comp in open_comps:
        if comp is main_open:
            continue
        for c in comp:
            layers[c] = palette_layer(c)
    black_space = main_open

    # distance from open black space; hidden rooms keep a solid shell
    black_dist = {c: 0 for c in black_space}
    dq = collections.deque(black_space)
    while dq:
        c = dq.popleft()
        for n in neighbours(c):
            if n not in black_dist:
                black_dist[n] = black_dist[c] + 1
                dq.append(n)

    # hidden rooms -----------------------------------------------------------
    room_cells = {}
    room_of = {}

    focus_pool = sorted((c for c in cells if dish_geom(c)[0] <= DISH_CORE + 1.0),
                        key=lambda c: dish_geom(c)[0])
    focus = set(focus_pool[:9])
    for c in focus:
        room_of[c] = 0
    room_cells[0] = sorted(focus)
    for c in focus:
        layers[c] = 3

    candidates = sorted(c for c in cells
                        if c not in black_space and c not in caps
                        and c not in trench and c not in lips
                        and c not in dish_cells
                        and black_dist.get(c, 0) >= 3
                        and outside_dist.get(c, 0) >= 4)
    rng.shuffle(candidates)
    rid = 1
    for seed_cell in candidates:
        if rid > ROOM_COUNT:
            break
        if seed_cell in room_of:
            continue
        want = rng.randint(ROOM_MIN, ROOM_MAX)
        blob = {seed_cell}
        frontier = [seed_cell]
        while len(blob) < want and frontier:
            u = frontier[rng.randrange(len(frontier))]
            options = [n for n in neighbours(u)
                       if n not in black_space and n not in caps
                       and n not in trench and n not in lips
                       and n not in dish_cells
                       and black_dist.get(n, 0) >= 3
                       and outside_dist.get(n, 0) >= 4
                       and n not in room_of and n not in blob]
            if not options:
                frontier.remove(u)
                continue
            v = rng.choice(options)
            blob.add(v)
            frontier.append(v)
        if len(blob) >= ROOM_MIN:
            for c in blob:
                room_of[c] = rid
                room_cells.setdefault(rid, []).append(c)
            rid += 1

    # a few underside rooms get a 2-3 cell pink/purple shell (sealed bunkers)
    room_shell = set()
    southern_rooms = [r for r, cs in room_cells.items() if gnorm(cs[0]) > 0.55]
    rng.shuffle(southern_rooms)
    for rid_sel in southern_rooms[:4]:
        ring = set(room_cells[rid_sel])
        for _ in range(2):
            ring |= {n for c in list(ring) for n in neighbours(c)}
        for c in ring:
            if (c not in room_of and c not in black_space and c not in caps
                    and c not in trench and c not in lips
                    and c not in dish_cells):
                room_shell.add(c)
                if layers[c] != 1:
                    layers[c] = 3 if patch_roll(c, 31, 5) < 55 else 5

    # green shards -----------------------------------------------------------
    greens = []
    occupied = set(room_of) | set(black_space) | set(caps)
    green_candidates = sorted(c for c in cells
                              if c not in occupied
                              and c not in trench and c not in lips
                              and c not in dish_cells)
    rng.shuffle(green_candidates)
    for c in green_candidates:
        if len(greens) >= GREEN_COUNT:
            break
        if all(hex_distance(c, g) >= 4 for g in greens):
            greens.append(c)

    # authored mod-material veins -------------------------------------------
    alt = {c: 0 for c in cells}
    special_cells = set()
    for code, target, sizes, (gmin, gmax), allow_rooms in SPECIAL_PLAN:
        placed = 0
        pool = sorted(c for c in cells
                      if c not in black_space and c not in caps and c not in greens
                      and c not in trench and c not in lips
                      and c not in dish_cells
                      and gmin <= gnorm(c) <= gmax
                      and (allow_rooms or c not in room_of)
                      and c not in special_cells)
        rng.shuffle(pool)
        for seed_cell in pool:
            if placed >= target:
                break
            if seed_cell in special_cells:
                continue
            want = min(rng.randint(sizes[0], sizes[1]), target - placed)
            blob = {seed_cell}
            frontier = [seed_cell]
            while len(blob) < want and frontier:
                u = frontier[rng.randrange(len(frontier))]
                opts = [n for n in neighbours(u)
                        if n in cells and n not in black_space and n not in caps
                        and n not in greens and n not in special_cells
                        and n not in trench and n not in lips
                        and n not in dish_cells
                        and gmin <= gnorm(n) <= gmax
                        and (allow_rooms or n not in room_of)]
                if not opts:
                    frontier.remove(u)
                    continue
                v = rng.choice(opts)
                blob.add(v)
                frontier.append(v)
            if len(blob) < sizes[0]:
                continue
            if any(hex_distance(c, p) <= 1 for c in blob for p in special_cells):
                continue
            for c in blob:
                alt[c] = code
                special_cells.add(c)
            placed += len(blob)

    # artifacts (power-up rolls) in hidden rooms -----------------------------
    artifacts = []
    focus_centre = min(focus, key=lambda c: dish_geom(c)[0])
    artifacts.append(focus_centre)
    for rid_sel in sorted(room_cells):
        if len(artifacts) >= ARTIFACT_COUNT:
            break
        if rid_sel == 0:
            continue
        options = sorted(c for c in room_cells[rid_sel]
                         if c not in black_space and c not in caps and alt[c] == 0)
        if options:
            artifacts.append(options[len(options) // 2])

    for c in caps:
        layers[c] = 4

    entrances = []
    if trench:
        ordered = sorted(trench, key=lambda c: screen(c)[0])
        entrances.append([ordered[0]])
        entrances.append([ordered[-1]])

    return {
        "cells": cells,
        "layers": layers,
        "alt": alt,
        "tunnel": black_space,
        "trench": trench,
        "caps": caps,
        "outside_dist": outside_dist,
        "room_cells": room_cells,
        "greens": greens,
        "artifacts": artifacts,
        "entrances": entrances,
        "room_shell": room_shell,
        "seed": seed,
        "scale": scale,
    }


# --------------------------------------------------------------------- output
def write_outputs(data: dict) -> None:
    cells = data["cells"]
    order = sorted(cells, key=lambda c: (c[1], c[0]))
    q = [c[0] for c in order]
    r = [c[1] for c in order]

    room_q, room_r, room_id = [], [], []
    for rid in sorted(data["room_cells"]):
        for c in sorted(data["room_cells"][rid]):
            room_q.append(c[0])
            room_r.append(c[1])
            room_id.append(rid)
    greens = data["greens"]

    map_obj = {
        "source": MAP_ID,
        "count": len(order),
        "q": q,
        "r": r,
        "alt": [data["alt"][c] for c in order],
        "layer": [data["layers"][c] for c in order],
        "bounds": {"q": [min(q), max(q)], "r": [min(r), max(r)]},
        "rooms": {"q": room_q, "r": room_r, "id": room_id},
        "roomGreen": {"q": [c[0] for c in greens], "r": [c[1] for c in greens]},
    }

    bands = [
        # layer, hpSealed, special_1..meta_1, explosive, lightning, void, swarm
        (1, 15, 0, 0, 0, 0, 4, 1, 1, 1),
        (2, 25, 0, 0, 0, 0, 10, 5, 5, 5),
        (3, 40, 0, 0, 0, 0, 19, 11, 11, 11),
        (4, 60, 0, 0, 0, 0, 10, 5, 5, 5),
        (5, 85, 0, 0, 0, 0, 17, 10, 10, 10),
    ]
    contract_obj = {
        "id": MAP_ID,
        "displayName": MAP_NAME,
        "description": MAP_DESC,
        "map": f"maps/{MAP_ID}.json",
        "cellCount": len(order),
        "sealedLayers": False,
        "startingMoney": 1000,
        "glyphCount": GLYPH_COUNT,
        "greenCount": len(greens),
        "bands": [
            {
                "layer": layer, "outerFrac": 1.0, "hpSealed": hp,
                "special1": s1, "special2": s2, "special3": s3, "meta1": m1,
                "explosive": ex, "lightning": li, "voidTiles": vo, "swarm": sw,
                "unsealedLook": 0,
            }
            for layer, hp, s1, s2, s3, m1, ex, li, vo, sw in bands
        ],
        "artifactCells": [[c[0], c[1]] for c in data["artifacts"]],
        "entrances": [[path[0][0], path[0][1]] for path in data["entrances"]],
    }

    (ROOT / "maps").mkdir(parents=True, exist_ok=True)
    (ROOT / "contracts").mkdir(parents=True, exist_ok=True)
    (ROOT / "previews").mkdir(parents=True, exist_ok=True)
    (ROOT / "maps" / f"{MAP_ID}.json").write_text(
        json.dumps(map_obj, separators=(",", ":")))
    (ROOT / "contracts" / f"{MAP_ID}.contract.json").write_text(
        json.dumps(contract_obj, indent=2) + "\n")
    write_preview(data, map_obj)

    counts = collections.Counter(data["layers"].values())
    total = len(order)
    print(f"{MAP_NAME} ({MAP_ID})")
    print(f"  cells      : {total}  bounds q{map_obj['bounds']['q']} r{map_obj['bounds']['r']}")
    print("  layers     : " + "  ".join(
        f"L{k}={counts[k]} ({100 * counts[k] / total:.1f}%)" for k in sorted(counts)))
    print(f"  trench     : {len(data['trench'])}  entrances: {len(data['entrances'])}")
    print(f"  rooms      : {len(data['room_cells'])}  green: {len(greens)}  "
          f"artifacts: {len(data['artifacts'])}  glyphs: {GLYPH_COUNT}")
    print(f"  specials   : {sum(1 for v in data['alt'].values() if v)}")
    print(f"  wrote maps/{MAP_ID}.json, contracts/{MAP_ID}.contract.json, "
          f"previews/{MAP_ID}.png")


def write_preview(data: dict, map_obj: dict) -> None:
    from PIL import Image, ImageDraw

    cells = data["cells"]
    px = [c[0] + c[1] * 0.5 for c in cells]
    py = [c[1] for c in cells]
    minx, maxx = min(px) - 3, max(px) + 3
    miny, maxy = min(py) - 3, max(py) + 3
    scale = 3.2
    pad = 16
    width = int((maxx - minx) * scale) + pad * 2
    height = int((maxy - miny) * scale) + pad * 2 + 58
    image = Image.new("RGB", (width, height), (12, 12, 16))
    draw = ImageDraw.Draw(image)

    def point(c):
        return ((c[0] + c[1] * 0.5 - minx) * scale + pad,
                (c[1] - miny) * scale + pad)

    for c in sorted(cells, key=lambda c: (c[1], c[0])):
        x, y = point(c)
        draw.regular_polygon((x, y, scale * 0.99), 6, rotation=0,
                             fill=LAYER_RGB[data["layers"][c]])

    for path in data["entrances"]:
        x, y = point(path[0])
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(255, 255, 255))

    labels = {1: "L1 black", 2: "L2 blue", 3: "L3 pink", 4: "L4 gold", 5: "L5 purple"}
    x = pad
    y = height - 40
    for layer in range(1, 6):
        draw.rectangle((x, y, x + 16, y + 16), fill=LAYER_RGB[layer])
        draw.text((x + 22, y + 3), labels[layer], fill=(220, 220, 230))
        x += 160
    draw.text((pad, height - 22),
              f"{MAP_NAME}  ·  {map_obj['count']} cells  ·  3/4 view  ·  "
              f"black panel grout + open bays  ·  white dots = entrances",
              fill=(200, 200, 210))
    image.save(ROOT / "previews" / f"{MAP_ID}.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE)
    parser.add_argument("--seed", type=lambda s: int(s, 0), default=DEFAULT_SEED)
    args = parser.parse_args()
    data = build(args.scale, args.seed)
    write_outputs(data)


if __name__ == "__main__":
    main()
