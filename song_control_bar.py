from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from filter_input import FilterInput
from player_controls import PlayerControls
from track_information import TrackInformation


class SongControlBar(Static):
    """The song control bar."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            PlayerControls(id="playback_controls"),
            Static("󰒞", id="playback_status")
        )
        yield TrackInformation(id="song_information")
        yield FilterInput("", placeholder="Filter", id="filter")
