from rich.text import Text
from textual.widgets import DataTable
from textual.widgets._data_table import RowKey  # noqa - required to extend DataTable

from const import TrackPath
from helpers import format_duration
from track import Track


class TrackList(DataTable):
    """The list of available tracks."""

    def on_mount(self) -> None:
        # TODO See if there is a way to expand a DataTable to full width.
        #      See: https://github.com/Textualize/textual/discussions/1942
        self.add_column(label="  ", width=2, key="status")
        self.add_columns("Title", "Artist", "Album", "Length", "Genre")
        self.cursor_type = "row"
        self.zebra_stripes = True

    def update_tracks(self, tracks: dict[TrackPath:object], playlist: list[TrackPath]) -> None:
        self.clear()
        for track_path in playlist:
            track: Track = tracks[track_path]
            track_row = [None, track.title, track.artist, track.album, track.duration, track.genre]
            track_row[4] = Text(format_duration(track.duration), justify="right")
            self.add_row(*track_row, key=track_path)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler for selecting a row in the data table."""
        self.app.select_track(event.row_key.value)

    def remove_icons(self) -> None:
        tracks = self.rows
        [self.update_cell(row_key=track_path, column_key="status", value="") for track_path in tracks.keys()]

    def set_icon(self, track_path: TrackPath, icon: str = "") -> None:
        self.update_cell(row_key=track_path, column_key="status", value=icon)

    def get_row_index_from_row_key(self, row_key: RowKey):
        return self._row_locations.get(row_key)
