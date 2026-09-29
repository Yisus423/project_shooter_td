"""Font loading for UI text.

One place to swap fonts: UI consumers ask for a font here instead of
loading TTFs directly, so replacing assets later touches this file only.
Fonts load once (Panda3D's loader caches by path).
"""


def menu_font(game):
    """Font for menus (title, controls, pause)."""
    return game.loader.loadFont("assets/fonts/font_menu.ttf")


def ingame_font(game):
    """Font for in-game HUD text."""
    return game.loader.loadFont("assets/fonts/font_ingame.ttf")
