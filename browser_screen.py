from os import path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Header, Footer

from directory_browser import DirectoryBrowser


class BrowserScreen(ModalScreen):
    BINDINGS = [
        Binding("o", "pop_screen()", "Close browser"),
        Binding("escape", "pop_screen()", "Close browser", show=False),
        Binding(".", "set_directory('.')", "Current"),
        Binding("~", "set_directory('~')", "Home"),
        Binding("/", "set_directory('/')", "Root"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DirectoryBrowser(id="directory_browser")
        yield Footer()

    def action_set_directory(self, directory: str) -> None:
        self.query_one(Browser).path = path.expanduser(directory)
        self.query_one(Browser).focus()
