#!/usr/bin/env python3
"""Generate the COW ABDUCTION contract map for Graveyard Orbit.

Design:
  * a saucer/dome UFO tractor-beaming a cow, ~50k hex cells;
  * a braided, 3-wide layer-1 maze, reachable from four gold-capped entrances
    on the planet side;
  * difficulty rises to the north: gold/blue walls in the south, purple/pink
    walls in the north;
  * 25-35% layer 1 (black) cells, concentrated in the lower maze;
  * authored mod-material veins clustered by tier, no procedural confetti;
  * enough beacons for two players to unlock all 20 relics (120 glyphs).

Outputs: maps/ufo_cow.json, contracts/ufo_cow.contract.json, previews/ufo_cow.png
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP_ID = "ufo_cow"
MAP_NAME = "COW ABDUCTION"
MAP_DESC = ("A saucer holds a very confused cow in its tractor beam. "
            "Four gold-capped entrances lead into a black maze under a "
            "purple-and-pink shell.")

DEFAULT_SEED = 0xC0FFEE
DEFAULT_SCALE = 1.096

MAZE_SPACING = 12
PLAZA_RADIUS = 2
PLAZA_CHANCE = 0.26
LOOP_CHANCE = 0.18

ROOM_COUNT = 24
ROOM_MIN, ROOM_MAX = 7, 19
GREEN_COUNT = 64
ARTIFACT_COUNT = 20
GLYPH_COUNT = 120          # 2 players x 20 relics x 3 beacons

# leg centres in base (unscaled) shape coordinates
LEG_X = (-33.5, -11.5, 22.5, 44.5)

# alt code, total cells, cluster size, latitude window (0=north, 1=south)
SPECIAL_PLAN = (
    (6, 110, (2, 4), (0.35, 1.00), False),  # special_1 gold, lower/mid
    (7, 90, (2, 3), (0.25, 0.85), False),   # special_2 red, mid
    (8, 60, (2, 3), (0.00, 0.65), False),   # special_3 blue, mid/north
    (9, 40, (1, 2), (0.00, 0.55), True),    # meta_1 green, north + rooms
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


# --------------------------------------------------------------------- shape
def _ellipse(x, y, cx, cy, a, b):
    return ((x - cx) / a) ** 2 + ((y - cy) / b) ** 2 <= 1.0


def _saucer(x, y):
    return (_ellipse(x, y, 0, -72, 120, 48)
            or _ellipse(x, y, 0, -58, 128, 24)
            or _ellipse(x, y, 0, -116, 44, 34))


def _beam(x, y):
    y0, y1 = -40.0, 96.0
    if not (y0 <= y <= y1):
        return False
    t = (y - y0) / (y1 - y0)
    return abs(x) <= 20.0 + (92.0 - 20.0) * t


def _cow(x, y):
    if _ellipse(x, y, 0, 108, 60, 34):
        return True
    if _ellipse(x, y, 64, 96, 24, 20):
        return True
    if _ellipse(x, y, 50, 78, 10, 7) or _ellipse(x, y, 78, 78, 10, 7):
        return True
    if _ellipse(x, y, 56, 72, 4, 9) or _ellipse(x, y, 72, 72, 4, 9):
        return True
    if _ellipse(x, y, -6, 130, 20, 12):
        return True
    for lx in (-40, -18, 16, 38):
        if lx <= x <= lx + 13 and 118 <= y <= 152:
            return True
    ax, ay, bx, by = -58.0, 112.0, -93.0, 141.0
    vx, vy = bx - ax, by - ay
    t = ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)
    if 0.0 <= t <= 1.0:
        px, py = ax + vx * t, ay + vy * t
        if (x - px) ** 2 + (y - py) ** 2 <= 20:
            return True
    return _ellipse(x, y, -96, 144, 11, 10)


def _region(x, y):
    if _cow(x, y):
        return "cow"
    if _beam(x, y):
        return "beam"
    return "ufo"


# ------------------------------------------------------------------- helpers
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

    cells = set()
    for r in range(-190, 190):
        for q in range(-380, 380):
            px, py = q + r * 0.5, r
            x, y = px / scale, py / scale
            if _saucer(x, y) or _beam(x, y) or _cow(x, y):
                cells.add((q, r))
    if not cells:
        raise SystemExit("empty shape")

    min_r = min(c[1] for c in cells)
    max_r = max(c[1] for c in cells)

    def gnorm(c):
        return (c[1] - min_r) / max(1, max_r - min_r)  # 0 north, 1 south

    def neighbours(c):
        q, r = c
        return [(q + dq, r + dr) for dq, dr in N6 if (q + dq, r + dr) in cells]

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

    # maze skeleton -----------------------------------------------------------
    off = MAZE_SPACING / 2
    nodes = {}
    node_px = {}
    for j in range(-28, 30):
        for i in range(-34, 34):
            px, py = i * MAZE_SPACING + off, j * MAZE_SPACING + off
            c = axial_cell(px, py)
            if c in cells and outside_dist.get(c, 0) >= 3:
                nodes[(i, j)] = c
                node_px[(i, j)] = (px, py)

    def path_between(a, b, margin=2):
        ax, ay = a
        bx, by = b
        steps = max(1, int(math.hypot(bx - ax, by - ay) / 0.45))
        out = []
        for k in range(steps + 1):
            t = k / steps
            c = axial_cell(ax + (bx - ax) * t, ay + (by - ay) * t)
            if c not in cells or outside_dist.get(c, 0) < margin:
                return None
            out.append(c)
        return out

    adjacency = collections.defaultdict(set)
    edge_paths = {}
    for (i, j) in nodes:
        for di, dj in ((1, 0), (0, 1)):
            k = (i + di, j + dj)
            if k in nodes:
                path = path_between(node_px[(i, j)], node_px[k])
                if path:
                    edge_paths[((i, j), k)] = path
                    adjacency[(i, j)].add(k)
                    adjacency[k].add((i, j))

    components = []
    seen = set()
    for n in nodes:
        if n in seen:
            continue
        comp, stack = [], [n]
        seen.add(n)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adjacency[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        components.append(comp)

    tree = set()
    for comp in components:
        root = comp[0]
        visited = {root}
        stack = [root]
        while stack:
            u = stack[-1]
            options = [v for v in adjacency[u] if v not in visited]
            if not options:
                stack.pop()
                continue
            v = rng.choice(options)
            tree.add((min(u, v), max(u, v)))
            visited.add(v)
            stack.append(v)

    active = [set(c) for c in components]
    while len(active) > 1:
        best = None
        for ai in range(len(active)):
            for bi in range(ai + 1, len(active)):
                for u in active[ai]:
                    ux, uy = node_px[u]
                    for v in active[bi]:
                        vx, vy = node_px[v]
                        d = (ux - vx) ** 2 + (uy - vy) ** 2
                        if best is None or d < best[0]:
                            best = (d, ai, bi, u, v)
        _, ai, bi, u, v = best
        tree.add((min(u, v), max(u, v)))
        active[ai] |= active[bi]
        active.pop(bi)

    loop_paths = []
    for (a, b), path in edge_paths.items():
        if (min(a, b), max(a, b)) not in tree and rng.random() < LOOP_CHANCE:
            loop_paths.append(path)

    centre = set()
    for (a, b), path in edge_paths.items():
        if (min(a, b), max(a, b)) in tree:
            centre.update(path)
    for path in loop_paths:
        centre.update(path)

    # black plazas at some southern/mid nodes
    plaza = set()
    for node, c in nodes.items():
        if gnorm(c) < 0.20 or rng.random() > PLAZA_CHANCE:
            continue
        for dq in range(-PLAZA_RADIUS, PLAZA_RADIUS + 1):
            for dr in range(-PLAZA_RADIUS, PLAZA_RADIUS + 1):
                if hex_distance((0, 0), (dq, dr)) <= PLAZA_RADIUS:
                    n = (c[0] + dq, c[1] + dr)
                    if n in cells and outside_dist.get(n, 0) >= 3:
                        plaza.add(n)
    centre.update(plaza)

    # carve the tail as a real corridor so its cells join the maze
    tail_pts = [(-58, 112), (-70, 122), (-82, 132), (-93, 141), (-96, 144)]
    for (ax, ay), (bx, by) in zip(tail_pts, tail_pts[1:]):
        ax, ay, bx, by = ax * scale, ay * scale, bx * scale, by * scale
        steps = max(1, int(math.hypot(bx - ax, by - ay) / 0.4))
        for k in range(steps + 1):
            t = k / steps
            c = axial_cell(ax + (bx - ax) * t, ay + (by - ay) * t)
            if c in cells:
                centre.add(c)

    # four entrances at the leg bottoms --------------------------------------
    def bfs_to(start, goals):
        prev = {start: None}
        dq = collections.deque([start])
        while dq:
            u = dq.popleft()
            if u in goals:
                path = []
                x = u
                while x is not None:
                    path.append(x)
                    x = prev[x]
                return path[::-1]
            for v in neighbours(u):
                if v not in prev:
                    prev[v] = u
                    dq.append(v)
        return None

    entrances = []
    for lx in LEG_X:
        target_x = lx * scale
        cands = [c for c in cells
                 if outside_dist.get(c, 0) == 1
                 and abs(c[0] + c[1] * 0.5 - target_x) <= 14 * scale]
        if not cands:
            continue
        mouth = max(cands, key=lambda c: c[1])
        path = bfs_to(mouth, centre)  # nearest maze cell through solid shape
        if path:
            entrances.append(path)
            centre.update(path)

    # three-wide tunnels ------------------------------------------------------
    tunnel = set()
    for c in centre:
        tunnel.add(c)
        tunnel.update(neighbours(c))

    entrance_keep = set()
    for path in entrances:
        for c in path:
            entrance_keep.add(c)
            entrance_keep.update(neighbours(c))
    tunnel = {c for c in tunnel if outside_dist.get(c, 0) >= 2 or c in entrance_keep}

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

    # gold cap: the first two *distinct* path cells plus the side cells of that
    # cross-section stay L4. This seals the full 3-wide mouth so no isolated
    # L1 side-lobe is left behind the plug.
    caps = set()
    for path in entrances:
        unique = []
        for c in path:
            if c not in unique:
                unique.append(c)
        core = set(unique[:2])
        beyond = set(unique[2:])
        caps |= core
        for c in core:
            for n in neighbours(c):
                if n in tunnel and n not in beyond:
                    caps.add(n)

    # layer assignment -------------------------------------------------------
    tunnel_dist = {c: 0 for c in tunnel}
    dq = collections.deque(tunnel)
    while dq:
        c = dq.popleft()
        for n in neighbours(c):
            if n not in tunnel_dist:
                tunnel_dist[n] = tunnel_dist[c] + 1
                dq.append(n)

    def roll(c, salt):
        return _hash(c, salt, seed) % 100

    def patch_roll(c, salt, block=5):
        px = c[0] + c[1] * 0.5
        key = (int(math.floor(px / block)), int(math.floor(c[1] / block)))
        return _hash(key, salt, seed) % 100

    def wall_layer(c):
        g = gnorm(c)
        td = tunnel_dist.get(c, 99)
        r = patch_roll(c, 11)
        if td == 1:
            if g > 0.62:                      # south: gold/blue, easy
                return 4 if r < 80 else 2
            if g > 0.35:                      # middle: blue/gold/purple
                return 2 if r < 50 else (4 if r < 74 else 5)
            return 5 if r < 60 else 3         # north: purple/pink
        if td == 2:
            if g > 0.62:
                return 4 if r < 55 else (2 if r < 85 else 5)
            if g > 0.35:
                return 4 if r < 30 else (2 if r < 60 else (5 if r < 80 else 3))
            return 3 if r < 50 else 5
        # deeper
        if g > 0.62:
            return 4 if r < 50 else (2 if r < 75 else (3 if r < 88 else 5))
        if g > 0.35:
            return 2 if r < 30 else (4 if r < 50 else (5 if r < 75 else 3))
        return 5 if r < 45 else (3 if r < 80 else 4)

    def deep_layer(c):
        g = gnorm(c)
        reg = _region((c[0] + c[1] * 0.5) / scale, c[1] / scale)
        r = patch_roll(c, 23)
        if reg == "cow":
            if g > 0.55:
                return 4 if r < 60 else (2 if r < 88 else (3 if r < 94 else 5))
            return 2 if r < 35 else (4 if r < 60 else (5 if r < 82 else 3))
        if g > 0.62:
            return 4 if r < 55 else (2 if r < 78 else (3 if r < 90 else 5))
        if g > 0.35:
            return 2 if r < 30 else (4 if r < 45 else (5 if r < 75 else 3))
        return 5 if r < 45 else (3 if r < 80 else 4)

    layers = {}
    for c in cells:
        if c in caps:
            layers[c] = 4
        elif c in tunnel:
            layers[c] = 1
        else:
            bd = outside_dist.get(c, 1)
            g = gnorm(c)
            if bd <= 2:
                layers[c] = 4 if g > 0.88 else 5
            elif tunnel_dist.get(c, 99) <= 2:
                layers[c] = wall_layer(c)
            else:
                layers[c] = deep_layer(c)

    # hidden rooms -----------------------------------------------------------
    room_cells = {}
    room_of = {}
    candidates = sorted(c for c in cells
                        if c not in tunnel and c not in caps
                        and tunnel_dist.get(c, 0) >= 4
                        and outside_dist.get(c, 0) >= 4)
    rng.shuffle(candidates)
    rid = 0
    for seed_cell in candidates:
        if rid >= ROOM_COUNT:
            break
        if seed_cell in room_of:
            continue
        want = rng.randint(ROOM_MIN, ROOM_MAX)
        blob = {seed_cell}
        frontier = [seed_cell]
        while len(blob) < want and frontier:
            u = frontier[rng.randrange(len(frontier))]
            options = [n for n in neighbours(u)
                       if n not in tunnel and n not in caps
                       and tunnel_dist.get(n, 0) >= 4
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

    # a few southern rooms get a 2-3 cell purple/pink shell despite the gradient
    room_shell = set()
    southern_rooms = [rid for rid, cs in room_cells.items() if gnorm(cs[0]) > 0.50]
    rng.shuffle(southern_rooms)
    for rid in southern_rooms[:6]:
        ring = set(room_cells[rid])
        for _ in range(2):
            ring |= {n for c in list(ring) for n in neighbours(c)}
        for c in ring:
            if c not in room_of and c not in tunnel and c not in caps:
                room_shell.add(c)
                if layers[c] != 1:
                    layers[c] = 3 if patch_roll(c, 31) < 55 else 5

    # green shards -----------------------------------------------------------
    greens = []
    occupied = set(room_of) | set(tunnel) | set(caps)
    green_candidates = sorted(c for c in cells
                              if c not in occupied and tunnel_dist.get(c, 0) >= 2)
    rng.shuffle(green_candidates)
    for c in green_candidates:
        if len(greens) >= GREEN_COUNT:
            break
        if all(hex_distance(c, g) >= 5 for g in greens):
            greens.append(c)

    # authored mod-material veins -------------------------------------------
    alt = {c: 0 for c in cells}
    special_cells = set()
    for code, target, sizes, (gmin, gmax), allow_rooms in SPECIAL_PLAN:
        placed = 0
        pool = sorted(c for c in cells
                      if c not in tunnel and c not in caps and c not in greens
                      and tunnel_dist.get(c, 0) >= 2
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
                        if n in cells and n not in tunnel and n not in caps
                        and n not in greens and n not in special_cells
                        and tunnel_dist.get(n, 0) >= 2
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
    for rid in sorted(room_cells):
        if len(artifacts) >= ARTIFACT_COUNT:
            break
        options = sorted(c for c in room_cells[rid]
                         if c not in tunnel and c not in caps and alt[c] == 0)
        if options:
            artifacts.append(options[len(options) // 2])

    # entrances: gold caps must not be overwritten by rooms/roomshell
    for c in caps:
        layers[c] = 4

    return {
        "cells": cells,
        "layers": layers,
        "alt": alt,
        "tunnel": tunnel,
        "caps": caps,
        "outside_dist": outside_dist,
        "tunnel_dist": tunnel_dist,
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
        (1, 15, 0, 0, 0, 0, 3, 1, 1, 1),
        (2, 25, 0, 0, 0, 0, 8, 4, 4, 4),
        (3, 40, 0, 0, 0, 0, 16, 9, 9, 9),
        (4, 60, 0, 0, 0, 0, 8, 4, 4, 4),
        (5, 85, 0, 0, 0, 0, 14, 8, 8, 8),
    ]
    contract_obj = {
        "id": MAP_ID,
        "displayName": MAP_NAME,
        "description": MAP_DESC,
        "map": f"maps/{MAP_ID}.json",
        "cellCount": len(order),
        "sealedLayers": False,
        "startingMoney": 4000,
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
    print(f"  tunnels    : {len(data['tunnel'])}  entrances: {len(data['entrances'])}")
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

    # mark the four entrances with a small white dot
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
              f"{MAP_NAME}  ·  {map_obj['count']} cells  ·  "
              f"white dots = gold-capped entrances  ·  north = harder",
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
