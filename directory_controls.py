from textual.app import ComposeResult
from textual.widgets import Static, Button


class DirectoryControls(Static):
    def compose(self) -> ComposeResult:
        yield Button("Select", id="directory_select")
        yield Button("Cancel", id="directory_cancel")
