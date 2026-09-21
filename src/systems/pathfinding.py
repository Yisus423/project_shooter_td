"""Pathfinding over the tile grid.

Stateless BFS: given world positions, returns the direction of the first
step toward the target, routing around non-walkable tiles. The grid is small
enough that recomputing per frame is cheap; caching would add state without
a measured need.

This is a module function, not a class like Physics/CollisionSystem: those
hold per-level state, this holds none.
"""
from collections import deque


def next_step(from_pos, to_pos, tiles, tile_size, width, height):
    """Return (dx, dy), the unit direction of the first step of a BFS path
    from from_pos toward to_pos over the tile grid, or None when unreachable.

    Cells with no tile entity count as walkable: spawn points do not
    generate tiles.
    """
    blocked = set()
    for tile in tiles:
        if not tile.walkable:
            blocked.add((tile.grid_x, tile.grid_y))

    start = (int(round(from_pos[0] / tile_size)), int(round(from_pos[1] / tile_size)))
    goal = (int(round(to_pos[0] / tile_size)), int(round(to_pos[1] / tile_size)))

    if start == goal or not _in_bounds(goal, width, height) or goal in blocked:
        return None

    # BFS from the goal backwards: parents recorded, stop when start is found.
    parents = {goal: None}
    queue = deque([goal])
    while queue:
        cell = queue.popleft()
        if cell == start:
            break
        for delta in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = (cell[0] + delta[0], cell[1] + delta[1])
            if neighbor in parents or neighbor in blocked or not _in_bounds(neighbor, width, height):
                continue
            parents[neighbor] = cell
            queue.append(neighbor)

    if start not in parents:
        return None

    first = parents[start]
    return (first[0] - start[0], first[1] - start[1])


def _in_bounds(cell, width, height):
    return 0 <= cell[0] < width and 0 <= cell[1] < height
