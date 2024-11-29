from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Placeholder


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("f1", "pop_screen()", "Close help"),
        Binding("escape", "pop_screen()", "Close help", show=False),
    ]

    def compose(self) -> ComposeResult:
        # TODO load help information from "HELP.md".
        yield Placeholder("TODO Help information will go here...")
