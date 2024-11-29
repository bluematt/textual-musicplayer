from os import path, walk

import pygame

from const import TrackPath, TRACK_EXT


def stripped_value_or_default(value: any, default: str) -> str:
    """Return a value (left and right trimmed) or a default, if it would be an empty string."""
    if not (value and str(value).strip()):
        return default
    return str(value).strip(" ")


def get_files_in_directory(directory: str) -> list[str]:
    """Return the selected media files (sorted) in the directory tree starting at `directory`."""
    if not path.exists(directory) or not path.isdir(directory):
        raise NotADirectoryError

    files = [
        TrackPath(path.join(dir_path, file))
        for (dir_path, _dir_names, filenames) in walk(directory)
        for file in filenames if file.endswith(TRACK_EXT) and not file.startswith(".")
    ]

    if len(files) == 0:
        raise FileNotFoundError

    files.sort()
    return files


def format_duration(duration: float) -> str:
    """Convert a duration in seconds into a minute/second string."""
    (m, s) = divmod(duration, 60.0)
    return f"{int(m)}\u2032{int(s):02}\u2033"  # unicode prime/double prime resp.


def init_pygame() -> None:
    """Initialise pygame for playback."""
    pygame.init()
    pygame.mixer.init()


def play_track(track_path: TrackPath) -> None:
    """Load media and start playback."""
    pygame.mixer.music.load(track_path)
    pygame.mixer.music.rewind()
    pygame.mixer.music.play(-1)


def unpause_playback() -> None:
    """Unpause playback."""
    pygame.mixer.music.unpause()


def pause_playback() -> None:
    """Pause playback."""
    pygame.mixer.music.pause()


def stop_playback() -> None:
    """Stop playback and unload the loaded media."""
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()


def get_playback_position() -> float:
    """Return the current playback position, in seconds."""
    return float(pygame.mixer.music.get_pos()) / 1000.0  # get_pos() returns a value in milliseconds
