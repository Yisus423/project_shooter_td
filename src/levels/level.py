import math

from src.entities.tile import Tile
from src.entities.player import Player
from src.entities.enemy import Enemy
from src.systems.physics import Physics
from src.systems.collision import CollisionSystem
from src.systems.animation_system import AnimationSystem
from src.systems.camera import CameraSystem


class Level:
    def __init__(self, game, level_data):
        self.game = game
        self.data = level_data
        self.tile_size = game.settings.get("game.tile_size", 1.0)

        self.tiles = []
        self._tile_map = {}
        self.entities = []
        self.projectiles = []
        self.melee_hitboxes = []
        self.player = None

        self.physics = Physics(game)
        self.collision = CollisionSystem(game)
        self.animation = AnimationSystem(game)
        self.camera = CameraSystem(game)

        self.root = self.game.render.attachNewNode("level_root")

    def build(self):
        self._build_tiles()
        self._build_player()
        self._build_enemies()
        self._setup_camera()

    def _build_tiles(self):
        for row in self.data["tiles"]:
            for tile_data in row:
                if tile_data["type"] == "spawn_player":
                    continue
                tile = Tile(self.game, tile_data, self.tile_size)
                tile.node.reparentTo(self.root)
                self.tiles.append(tile)
                self._tile_map[(tile.grid_x, tile.grid_y)] = tile

    def tile_at(self, grid_x, grid_y):
        """Return the tile at a grid cell, or None when the cell is empty.

        Uses an O(1) dict lookup instead of scanning the flat tile list.
        """
        return self._tile_map.get((grid_x, grid_y))

    def has_line_of_sight(self, from_pos, to_pos):
        """Return True when no non-walkable tile blocks the straight line
        between two world positions.

        Used by enemy AI perception: a wall (or any non-walkable tile) between
        an enemy and the player breaks sight, melee bites, and shots.

        The segment is traversed with an Amanatides-Woo style grid DDA:
        starting from the shooter's cell, we repeatedly cross the nearest cell
        boundary until we reach the target cell, visiting every cell the
        segment passes through. Diagonals are lenient: a ray that crosses an
        exact cell corner visits only the diagonal cell, so squeezing exactly
        through a corner is allowed.

        The start and end cells are never checked: the shooter's own tile must
        not block the ray, and the target tile is the player's. Cells without
        a tile entry (e.g. the player spawn) are treated as open ground.

        Args:
            from_pos: World (x, y) of the observer.
            to_pos: World (x, y) of the target.

        Returns:
            True when the segment crosses only walkable (or empty) cells.
        """
        ts = self.tile_size

        # Cell index for a coordinate c matches Character.move()'s
        # int(round(pos / tile_size)) for on-center positions.
        start_cell = (
            int(round(from_pos[0] / ts)),
            int(round(from_pos[1] / ts)),
        )
        end_cell = (
            int(round(to_pos[0] / ts)),
            int(round(to_pos[1] / ts)),
        )

        # Shooter and player share a cell: nothing can be in between.
        if start_cell == end_cell:
            return True

        # Convert to grid space: cell centers sit at integer coordinates and
        # cell boundaries at half-integers.
        u0 = from_pos[0] / ts
        v0 = from_pos[1] / ts
        du = to_pos[0] / ts - u0
        dv = to_pos[1] / ts - v0

        step_u = 1 if du > 0 else -1
        step_v = 1 if dv > 0 else -1

        # t is the parametric position along the segment (0 at from_pos, 1 at
        # to_pos). tDelta is the t step needed to cross one full cell along
        # each axis; an axis-aligned ray never crosses boundaries on the other
        # axis, so its tDelta is infinity.
        t_delta_u = math.inf if du == 0 else abs(1.0 / du)
        t_delta_v = math.inf if dv == 0 else abs(1.0 / dv)

        # tMax is the t at which the ray crosses the first boundary of the
        # start cell on each axis.
        if du > 0:
            t_max_u = (start_cell[0] + 0.5 - u0) / du
        elif du < 0:
            t_max_u = (start_cell[0] - 0.5 - u0) / du
        else:
            t_max_u = math.inf

        if dv > 0:
            t_max_v = (start_cell[1] + 0.5 - v0) / dv
        elif dv < 0:
            t_max_v = (start_cell[1] - 0.5 - v0) / dv
        else:
            t_max_v = math.inf

        gx, gy = start_cell
        while (gx, gy) != end_cell:
            # Cross whichever boundary comes first along the ray. When the
            # next crossing lies beyond the end of the segment, the target
            # cell has effectively been reached (float rounding may skip the
            # exact end cell): stop without blocking sight.
            if t_max_u < t_max_v:
                if t_max_u > 1.0:
                    break
                gx += step_u
                t_max_u += t_delta_u
            elif t_max_v < t_max_u:
                if t_max_v > 1.0:
                    break
                gy += step_v
                t_max_v += t_delta_v
            else:
                # Exact corner crossing: step both axes at once so only the
                # diagonal cell is visited (symmetric lenient policy).
                if t_max_u > 1.0:
                    break
                gx += step_u
                t_max_u += t_delta_u
                gy += step_v
                t_max_v += t_delta_v

            # Skip the end cell: that is the player's tile.
            if (gx, gy) == end_cell:
                break

            tile = self.tile_at(gx, gy)
            if tile is not None and not tile.walkable:
                return False

        return True

    def _build_player(self):
        spawn = self.data["player_spawn"]
        if spawn is None:
            spawn = (0, 0)

        model_name = "models/smiley"
        self.player = Player(
            self.game,
            model_name=model_name,
            grid_pos=spawn,
            tile_size=self.tile_size,
        )
        self.player.node.reparentTo(self.root)
        self.entities.append(self.player)
        self.game.input_manager.bind_player(self.player)

    def _build_enemies(self):
        model_name = "models/panda-model"
        for spawn in self.data["enemy_spawns"]:
            enemy = Enemy(
                self.game,
                model_name=model_name,
                grid_pos=spawn,
                tile_size=self.tile_size,
            )
            enemy.node.reparentTo(self.root)
            self.entities.append(enemy)

    def _setup_camera(self):
        width = self.data["width"] * self.tile_size
        height = self.data["height"] * self.tile_size
        center_x = width / 2.0
        center_y = height / 2.0
        self.camera.setup(center_x, center_y)

    def update(self, dt):
        self.physics.update(dt, self.entities + self.projectiles, self.tiles)
        self.collision.update(dt, self.entities, self.projectiles, self.tiles, self.melee_hitboxes)
        self.animation.update(dt)
        self.camera.update(dt)

        for projectile in self.projectiles[:]:
            projectile.update(dt)
            if projectile.should_destroy():
                self.remove_projectile(projectile)

        for entity in self.entities[:]:
            entity.update(dt)
            if entity.is_dead():
                self.remove_entity(entity)
                # player death changes state (destroys this level): stop iterating
                if self.game.state_machine.current_name != "gameplay":
                    break

        for hb in self.melee_hitboxes[:]:
            hb.update(dt)
            if not hb.alive:
                self.remove_melee_hitbox(hb)

    def add_projectile(self, projectile):
        projectile.node.reparentTo(self.root)
        self.projectiles.append(projectile)

    def add_melee_hitbox(self, hitbox):
        hitbox.node.reparentTo(self.root)
        self.melee_hitboxes.append(hitbox)

    def remove_melee_hitbox(self, hitbox):
        if hitbox in self.melee_hitboxes:
            self.melee_hitboxes.remove(hitbox)
            hitbox.destroy()

    def remove_projectile(self, projectile):
        if projectile in self.projectiles:
            self.projectiles.remove(projectile)
            projectile.destroy()

    def remove_entity(self, entity):
        if entity == self.player:
            entity.destroy()
            self.player = None
            self.game.state_machine.change_state("menu")
            return
        if entity in self.entities:
            self.entities.remove(entity)
            entity.destroy()

    def destroy(self):
        for entity in self.entities:
            entity.destroy()
        for projectile in self.projectiles:
            projectile.destroy()
        for hb in self.melee_hitboxes:
            hb.destroy()
        for tile in self.tiles:
            tile.destroy()
        self.entities.clear()
        self.projectiles.clear()
        self.melee_hitboxes.clear()
        self.tiles.clear()
        self.root.removeNode()
