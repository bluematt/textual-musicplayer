from textual.app import ComposeResult
from textual.widgets import Static, ProgressBar

from helpers import format_duration


class TrackProgress(Static):
    """Display the progress of a track."""

    def compose(self) -> ComposeResult:
        yield Static(format_duration(0.0), id="track_current_time")
        yield ProgressBar(total=None, show_eta=False, show_percentage=False, id="progress_bar")
        yield Static(format_duration(0.0), id="track_total_time")
