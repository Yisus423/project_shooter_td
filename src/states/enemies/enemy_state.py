class EnemyState:
    """Base class for enemy AI states.

    Reuses the StateBase contract (enter/exit/update) but is NOT registered
    in the global StateMachine: these are per-entity behavior states, each
    Enemy owns its own instance.
    """

    def __init__(self, enemy):
        self.enemy = enemy

    def enter(self):
        pass

    def exit(self):
        pass

    def update(self, dt):
        pass

    def _player_context(self):
        """Return (nx, ny, dist, level) toward the player, or None.

        Returns None when not in gameplay, when there is no player, or when
        the player is exactly on top of the enemy (dist == 0). This mirrors
        the guards of the original Enemy._update_ai.
        """
        game = self.enemy.game
        if game.state_machine.current_name != "gameplay":
            return None

        gameplay = game.state_machine.get_state("gameplay")
        if not gameplay or not gameplay.level or not gameplay.level.player:
            return None

        player = gameplay.level.player
        player_pos = player.get_position()
        my_pos = self.enemy.get_position()

        dx = player_pos[0] - my_pos[0]
        dy = player_pos[1] - my_pos[1]
        dist = (dx**2 + dy**2) ** 0.5

        if dist <= 0:
            return None

        return (dx / dist, dy / dist, dist, gameplay.level)

    def _can_see_player(self, context):
        """Shared perception rule for all states: True when no non-walkable
        tile blocks the straight line from this enemy to the player.

        `context` is the tuple returned by _player_context(); its level is
        used to raycast between the two world positions.
        """
        _, _, _, level = context
        return level.has_line_of_sight(
            self.enemy.get_position(), level.player.get_position()
        )
