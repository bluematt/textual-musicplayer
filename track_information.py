from textual.app import ComposeResult
from textual.widgets import Static

from const import ALBUM_UNKNOWN, ARTIST_UNKNOWN, TRACK_UNKNOWN
from track_progress import TrackProgress


class TrackInformation(Static):
    """Display information about a track."""

    def compose(self) -> ComposeResult:
        yield Static(TRACK_UNKNOWN, id="title")
        yield Static(ARTIST_UNKNOWN, id="artist")
        yield Static(ALBUM_UNKNOWN, id="album")
        yield TrackProgress()
