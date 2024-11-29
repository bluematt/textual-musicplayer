from textual.app import ComposeResult
from textual.widgets import Static

from const import NO_ARTWORK


class AlbumArtwork(Static):
    """Container for album artwork."""

    def compose(self) -> ComposeResult:
        yield Static(NO_ARTWORK, id="album_artwork")
