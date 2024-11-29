"""A simple music player (MP3, etc.) using [Textual](https://textual.textualize.io/)."""

from __future__ import annotations

from os import environ

from helpers import format_duration, init_pygame
from music_player_app import MusicPlayerApp

# Hide the Pygame prompts from the terminal.
# Imported libraries should *not* dump to the terminal...
# See https://github.com/pygame/pygame/issues/1468
# This may show as a warning in IDEs that support PEP 8 (E402) that don't support 'noqa'.
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "True"

if __name__ == "__main__":
    # Add path to the dynamic libraries
    # TODO Is this actually required, or are libraries already on the path?
    # sys.path.append(PATH_DYLIBS)

    # Initialize pygame for music playback.
    init_pygame()

    # Run the app.
    app = MusicPlayerApp()
    # app.cwd = "./demo_music"
    app.run()
