from textual.app import ComposeResult
from textual.widgets import Static, Button


class PlayerControls(Static):
    """Playback controls."""

    def compose(self) -> ComposeResult:
        yield Button("|<", id="previous_track")
        yield Button("|>", id="play")
        yield Button("||", id="pause")
        yield Button(">|", id="next_track")
