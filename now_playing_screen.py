from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Header, Static, Footer

from album_artwork import AlbumArtwork
from player_controls import PlayerControls
from track_information import TrackInformation


class NowPlayingScreen(Screen):
    """Screen that displays the currently playing track and album artwork."""
    BINDINGS = [
        Binding("space", "app.play_pause", "|>/||"),
        Binding("left_square_bracket", "app.previous_track", "<<"),
        Binding("right_square_bracket", "app.next_track", ">>"),
        Binding("p", "app.pop_screen()", "Tracks"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield AlbumArtwork()
        yield Vertical(
            TrackInformation(id="song_information"),
            PlayerControls(id="playback_controls"),
            Static("󰒞", id="playback_status")
        )
        # yield Static("", id="status_bar", disabled=True)
        yield Footer()
