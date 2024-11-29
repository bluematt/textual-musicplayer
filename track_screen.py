from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Input, Static

from song_control_bar import SongControlBar
from track_list import TrackList


class TrackScreen(Screen):
    """Screen that displays the track list."""

    BINDINGS = [
        Binding("space", "app.play_pause", "|>/||"),
        Binding("left_square_bracket", "app.previous_track", "<<"),
        Binding("right_square_bracket", "app.next_track", ">>"),
        Binding("p", "app.push_screen('now_playing')", "Now playing"),
        Binding("ctrl+f", "focus_filter", "Filter"),
        Binding("ctrl+x", "clear_filter", "Clear filter", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MusicPlayer()
        yield Footer()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_clear_filter(self):
        self.query_one("#filter", Input).value = ""
        self.app.filter_playlist()


class MusicPlayer(Static):
    def compose(self) -> ComposeResult:
        yield SongControlBar(id="song_control_bar")
        yield TrackList(id="track_list")
        yield Static("", id="status_bar")
