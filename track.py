from __future__ import annotations

from io import BytesIO
from PIL import Image

from rich_pixels import Pixels
from tinytag import TinyTag

from const import TRACK_UNKNOWN, ARTIST_UNKNOWN, ALBUM_UNKNOWN, ARTWORK_DIMENSIONS, NO_ARTWORK
from helpers import stripped_value_or_default


class Track:
    """Convenience decorator for `TinyTag`."""
    track: TinyTag

    def __init__(self, track: TinyTag):
        self.track = track

    @property
    def title(self) -> str:
        """Return the track's title or a sane default."""
        return stripped_value_or_default(self.track.title, TRACK_UNKNOWN)

    @property
    def artist(self) -> str:
        """Return the track's artist or a sane default."""
        return stripped_value_or_default(self.track.artist, ARTIST_UNKNOWN)

    @property
    def album(self) -> str:
        """Return the track's album title or a sane default."""
        return stripped_value_or_default(self.track.album, ALBUM_UNKNOWN)

    @property
    def genre(self):
        """Return the track's genre."""
        return self.track.genre

    @property
    def duration(self):
        """Return the track's duration."""
        return self.track.duration

    @property
    def image(self) -> Pixels | str:
        """Return the track's image, if available."""
        image_data = self.track.get_image()
        if image_data:
            image: Image = Image.open(BytesIO(image_data))
            return Pixels.from_image(image.resize(size=ARTWORK_DIMENSIONS))
        return NO_ARTWORK

    def contains(self, filter_str: str):
        """Return whether `filter_str` (or part thereof) is (naïvely) somewhere within the track's information."""
        filters = filter_str.lower().split(" ")
        search = f"{self.title} {self.artist} {self.album} {self.genre}".lower()
        return all(f in search for f in filters)

    def __repr__(self):
        return f"{self.title} by {self.artist}"
