from os import path
from os.path import abspath
from pathlib import Path
from typing import Optional, Iterable

from textual import on
from textual.app import ComposeResult
from textual.reactive import Reactive
from textual.widgets import Static, Button
from textual.widgets._directory_tree import DirEntry, DirectoryTree  # noqa - required to extend DirectoryTree

from directory_controls import DirectoryControls


class DirectoryBrowser(Static):
    directory: Reactive[Optional[DirEntry]] = Reactive(".")

    def compose(self) -> ComposeResult:
        yield Static("", id="browser_directory")
        yield Browser(path=self.directory, id="browser")
        yield DirectoryControls()

    def on_mount(self):
        self.query_one(Browser).focus()

    def watch_directory(self):
        self.query_one("#browser_directory", Static).update(abspath(path.expanduser(self.directory.path)))

    @on(Button.Pressed, "#directory_cancel")
    def close_browser(self) -> None:
        self.app.pop_screen()

    @on(Button.Pressed, "#directory_select")
    def select_directory(self) -> None:
        self.app.open_directory(self.directory)
        self.app.pop_screen()


class Browser(DirectoryTree):
    def on_tree_node_selected(self, event: DirectoryTree.NodeSelected):
        self.app.query_one(DirectoryBrowser).directory = event.node.data

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter paths to non-hidden directories only."""
        return [p for p in paths if p.is_dir() and not p.name.startswith(".")]
