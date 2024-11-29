from textual.binding import Binding
from textual.widgets import Input


class FilterInput(Input):
    last_filter: str = ""

    BINDINGS = [
        Binding("escape", "unfocus_filter", "Unfocus", show=False),
    ]

    def action_unfocus_filter(self) -> None:
        if self.value != self.last_filter:
            self.value = self.last_filter
        self.app.get_track_list_widget().focus()

    def action_submit(self) -> None:
        self.last_filter = self.value
        self.app.filter_playlist(self.value)
