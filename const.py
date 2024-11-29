# Type aliases
TrackPath = str

# Path to binaries.
PATH_DYLIBS: str = "./venv/lib/python3.7/site-packages/pygame/.dylibs"

# The supported file types.
# TODO Determine while audio file types are/can be supported.
TRACK_EXT: tuple[str, ...] = (".mp3", ".ogg",)  # ".mp4",  ".m4a", ".flac" - currently unsupported

# Localisation.
TRACK_UNKNOWN: str = "<unknown track>"
ARTIST_UNKNOWN: str = "<unknown artist>"
ALBUM_UNKNOWN: str = "<unknown album>"
NO_ARTWORK: str = "<no embedded album art>"

# How often the UI is updated.
FRAME_RATE: float = 1.0 / 30.0  # 30 Hz

# Artwork size
ARTWORK_DIMENSIONS: tuple[int, int] = (24, 24)
