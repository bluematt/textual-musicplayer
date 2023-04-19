from __future__ import annotations

import sys

from os import walk, path, environ
from pathlib import Path
from typing import ClassVar, Iterable

from rich.console import RenderableType
from textual.binding import Binding
from textual.message import Message
from tinytag import TinyTag

from textual import log
from textual.reactive import reactive
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Horizontal, Center, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Switch, Label, DataTable, ContentSwitcher, Placeholder, \
    DirectoryTree, Tree
from tinytag.tinytag import ID3, Ogg, Wave, Flac, Wma, MP4, Aiff

# Hide the Pygame prompts from the terminal.
# Imported libraries should *not* dump to the terminal...
# See https://github.com/pygame/pygame/issues/1468
# This may show as a warning in IDEs that support PEP 8 (E402) that don't support 'noqa'.
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "True"
import pygame  # noqa: E402

TrackType = TinyTag | ID3 | Ogg | Wave | Flac | Wma | MP4 | Aiff
Track = tuple[str, ...]

# Path to binaries.
PATH_DYLIBS: str = "./venv/lib/python3.7/site-packages/pygame/.dylibs"

# Index of the title column of the Track tuple.
TRACK_TITLE_OFFSET: int = 0
# Index of the artist column of the Track tuple.
TRACK_ARTIST_OFFSET: int = 1
# Index of the album column of the Track tuple.
TRACK_ALBUM_OFFSET: int = 2
# Index of the duration column of the Track tuple.
TRACK_DURATION_OFFSET: int = 3
# Index of the file column of the Track tuple.
TRACK_FILE_OFFSET: int = 5

# The supported file types.
# TODO Determine while audio file types are/can be supported.
TRACK_EXT: tuple[str, ...] = (".mp3",
                              # ".mp4",
                              # ".m4a",
                              # ".ogg",
                              # ".flac"
                              )

SYM_PLAY: str = "\u25B6"  # ▶️
SYM_PAUSE: str = "\u23F8"  # ⏸️
SYM_PLAY_PAUSE: str = "\u23EF"  # ⏯️
SYM_REPEAT: str = "\U0001F501"  # 🔁
SYM_RANDOM: str = "\U0001F500"  # 🔀
SYM_SPEAKER: str = "\U0001F508"  # 🔈
SYM_SPEAKER_MUTED: str = "\U0001F507"  # 🔇

LBL_TRACK_UNKNOWN: str = "<unknown track>"
LBL_ARTIST_UNKNOWN: str = "<unknown artist>"
LBL_ALBUM_UNKNOWN: str = "<unknown album>"
LBL_REPEAT: str = "Repeat"
LBL_RANDOM: str = "Random"


class TitleInfo(Static):
    """The track title."""
    title: reactive[str] = reactive(LBL_TRACK_UNKNOWN)

    def render(self) -> RenderableType:
        return f"[bold]{self.title}[/]" if self.title else f"[bold]{LBL_TRACK_UNKNOWN}[/]"


class ArtistInfo(Static):
    """The track artist."""
    artist: reactive[str] = reactive(LBL_ARTIST_UNKNOWN)

    def render(self) -> RenderableType:
        return f"{self.artist}" if self.artist else LBL_ARTIST_UNKNOWN


class AlbumInfo(Static):
    """The track album."""
    album: reactive[str] = reactive(LBL_ALBUM_UNKNOWN)

    def render(self) -> RenderableType:
        return f"[italic]{self.album}[/]" if self.album else f"[italic]{LBL_ALBUM_UNKNOWN}[/]"


class TrackInformation(Static):
    """The track information."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            TitleInfo(LBL_TRACK_UNKNOWN, id="track_name"),
            ArtistInfo(LBL_ARTIST_UNKNOWN, id="artist_name"),
            AlbumInfo(LBL_ALBUM_UNKNOWN, id="album_name")
        )


class PlayerControls(Static):
    """The music controls."""

    def compose(self) -> ComposeResult:
        yield Center(Horizontal(
            Button(SYM_PLAY, id="play_button"),
            Button(SYM_PAUSE, id="pause_button"),
            Horizontal(
                Label(SYM_REPEAT + LBL_REPEAT, classes="label"),
                Switch(value=False, id="repeat_switch", disabled=True),
                classes="container",
            ),
            Horizontal(
                Label(SYM_RANDOM + LBL_RANDOM, classes="label"),
                Switch(value=False, id="random_switch", disabled=True),
                classes="container",
            ),
        ))


class TrackList(VerticalScroll):
    """The scrollable list of tracks."""

    def compose(self) -> ComposeResult:
        playlist = DataTable(id="playlist")
        playlist.cursor_type = "row"
        playlist.zebra_stripes = True

        yield playlist


class DirectoryBrowser(DirectoryTree):
    """The directory browser."""
    BINDINGS = [
        Binding("h", "home", "Home directory"),
        Binding("r", "root", "Root directory"),
        Binding("o", "close_directory", "Close directory browser"),
    ]

    class DirectorySelected(Message):
        directory: str

        def __init__(self, directory: str):
            self.directory = directory
            super().__init__()

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter paths to non-hidden directories only."""
        return [p for p in paths if p.is_dir() and not p.name.startswith(".")]

    def on_tree_node_selected(self, event: DirectoryBrowser.NodeSelected):
        """Handler for selecting a directory in the directory browser."""
        self.post_message(self.DirectorySelected(event.node.data.path))


class NowPlaying(Placeholder):
    """Display what is currently playing."""
    BINDINGS = []

    title: reactive[str] = reactive("")
    artist: reactive[str] = reactive("")
    album: reactive[str] = reactive("")
    artwork = None


class MusicPlayer(Static):
    """The main music player user interface."""

    def compose(self) -> ComposeResult:
        yield TrackInformation()
        yield PlayerControls()
        yield ContentSwitcher(
            TrackList(id="tracklist"),
            DirectoryBrowser(path=path.expanduser("~"), id="directory_browser"),
            NowPlaying(id="now_playing"),
            id="context",
            initial="tracklist"
        )


def format_duration(duration: float) -> str:
    """Converts a duration in seconds into a minute/second string."""
    (m, s) = divmod(duration, 60.0)
    return f"{int(m)}\u2032{int(s):02}\u2033"


def stop_music() -> None:
    """Stop playback."""
    pygame.mixer.init()
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()


def pause() -> None:
    """Pause playback."""
    pygame.mixer.init()
    pygame.mixer.music.pause()


def unpause() -> None:
    """Unpause playback."""
    pygame.mixer.init()
    pygame.mixer.music.unpause()


def toggle_mute() -> None:
    """Toggle mute."""
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0 - pygame.mixer.music.get_volume())


def is_playing() -> bool:
    """Return whether a track is currently playing."""
    pygame.mixer.init()
    return pygame.mixer.music.get_busy()


def play_track(track: Track) -> None:
    if not track or not track[TRACK_FILE_OFFSET]:
        log("NO TRACK")
        return

    pygame.mixer.init()
    pygame.mixer.music.load(track[TRACK_FILE_OFFSET])
    pygame.mixer.music.play()


class MusicPlayerApp(App):
    """A music player app."""

    TITLE = "tTunes"  # 😏
    CSS_PATH: ClassVar[CSSPathType | None] = "music_player.css"
    BINDINGS = [
        ("space", "toggle_play", SYM_PLAY_PAUSE),
        ("m", "toggle_mute", "Mute/Unmute"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("o", "open_directory", "Open directory"),
        ("r", "toggle_repeat", "Toggle repeat"),
        ("n", "toggle_random", "Toggle random"),
        ("p", "toggle_now_playing", "Now playing"),
        ("q", "quit", "Quit"),
    ]

    # The current working directory (where music files are).
    cwd: reactive[str] = reactive("./demo_music")

    # The list of current tracks.
    tracks: reactive[list[tuple]] = reactive([])

    # The current track.
    current_track: reactive[Track | None] = reactive(None)

    # The ID of the previous context widget.
    previous_context: str = "tracklist"

    # def watch_cwd(self) -> None:
    #     """Watch for changes to `cwd`."""
    #     log("CWD CHANGED")
    #     self.scan_track_directory()

    # def watch_tracks(self) -> None:
    #     """Watch for changes to `tracks`."""
    #     log("PLAYLIST UPDATED")
    #     self.update_track_list()

    def watch_current_track(self) -> None:
        """Watch for changes to `current_track`."""
        log("CURRENT_TRACK_CHANGED")
        self.play_current_track()

    def play_current_track(self) -> None:
        """Play the current track."""
        self.play_track(self.current_track)

    def compose(self) -> ComposeResult:
        """Render the music player."""
        yield Header(show_clock=True)
        yield MusicPlayer()
        yield Footer()

    def on_mount(self) -> None:
        """Mount the application."""
        # Scan for music in the current working directory.
        self.scan_track_directory()
        self.update_playlist()

        # Focus the playlist
        self.focus_playlist()

        # Set the current track to be the first track in the playlist.
        # TODO Error handling for empty playlists.
        self.current_track = tuple(self.get_playlist().get_row_at(0))

    def update_playlist(self) -> None:
        """Update the playlist with the tracks from the current working directory."""
        playlist: DataTable = self.get_playlist()
        playlist.clear(columns=True)
        tracks = iter(self.tracks)
        playlist.add_columns(*next(tracks))
        playlist.add_rows(tracks)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_toggle_play(self) -> None:
        """Toggle play/pause."""
        pygame.mixer.init()
        if is_playing():
            pause()
        else:
            unpause()

    def action_toggle_now_playing(self) -> None:
        """Toggle the 'now playing' context."""
        current_context: str = self.query_one("#context", ContentSwitcher).current
        if current_context == "now_playing":
            self.query_one("#context", ContentSwitcher).current = self.previous_context
        else:
            self.previous_context = current_context
            self.query_one("#context", ContentSwitcher).current = "now_playing"

    def action_toggle_mute(self) -> None:
        toggle_mute()

    def action_toggle_repeat(self) -> None:
        """Toggle repeating."""
        repeat_switch = self.query_one("#repeat_switch", Switch)
        repeat_switch.toggle()

    def action_toggle_random(self) -> None:
        """Toggle playlist randomisation."""
        random_switch = self.query_one("#random_switch", Switch)
        random_switch.toggle()

    def action_open_directory(self) -> None:
        self.set_context("directory_browser")
        # self.query_one("#context", ContentSwitcher).current = "directory_browser"
        self.set_focus(self.query_one("#directory_browser", DirectoryBrowser))

    def action_close_directory(self) -> None:
        self.query_one("#context").current = "tracklist"

    def scan_track_directory(self) -> None:
        """Scan the current working directory for music files."""
        files = self.get_files_in_directory(self.cwd)
        self.update_tracks_from_files(files)

    def update_tracks_from_files(self, files: list) -> None:
        # Get track metadata from music files.
        tracks: list[TrackType] = [TinyTag.get(f) for f in files]

        # Create a list of tuple(track info).
        track_data: list[Track] = [("Title", "Artist", "Album", "Length", "Genre", "File"), ]
        [track_data.append((t.title, t.artist, t.album, format_duration(t.duration), t.genre, files[idx])) for
         idx, t in enumerate(tracks)]

        self.tracks = track_data

    def update_track_info(self, track: Track) -> None:
        """Update the UI with details of the current track."""
        self.query_one("#track_name").title = track[TRACK_TITLE_OFFSET]
        self.query_one("#artist_name").artist = track[TRACK_ARTIST_OFFSET]
        self.query_one("#album_name").album = track[TRACK_ALBUM_OFFSET]
        log(track)

    def play_track(self, track: Track) -> None:
        """Play a track."""
        if track:
            if is_playing():
                stop_music()

            play_track(track)
            self.update_track_info(track)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "play_button":
            unpause()
        if event.button.id == "pause_button":
            pause()

        self.focus_playlist()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        log(event.switch.id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler for selecting a row in the data table."""
        self.current_track = tuple(event.data_table.get_row_at(event.cursor_row))

    def on_directory_browser_directory_selected(self, event: DirectoryBrowser.DirectorySelected):
        """Handler for selecting a directory in the directory browser."""
        files = self.get_files_in_directory(event.directory)
        if len(files) <= 0:
            log(f"NO USABLE FILES IN DIRECTORY {event.directory}")
            return

        stop_music()
        self.set_working_directory(event.directory)
        self.focus_playlist()

    def get_playlist(self) -> DataTable:
        """Return the playlist widget."""
        return self.query_one("#playlist", DataTable)

    def focus_playlist(self) -> None:
        """Sets the context to the tracklist and focuses the playlist."""
        self.set_context("tracklist")
        self.set_focus(self.get_playlist())

    def set_context(self, context: str) -> None:
        """Sets the context for the main context panel."""
        self.previous_context = self.query_one("#context", ContentSwitcher).current
        self.query_one("#context", ContentSwitcher).current = context

    def set_working_directory(self, directory: str) -> None:
        """Sets the current working directory, rescans the files therein and updates the playlist."""
        self.cwd = directory
        self.scan_track_directory()
        self.update_playlist()

    def get_files_in_directory(self, directory: str) -> list[bytes | str]:
        """Returns the list of files in the directory."""
        if not path.exists(directory) or not path.isdir(directory):
            raise FileNotFoundError

        return [
            path.join(dir_path, f)
            for (dir_path, _dir_names, filenames) in walk(directory)
            for f in filenames if f.endswith(TRACK_EXT) and not f.startswith(".")
        ]


if __name__ == "__main__":
    # Add path to the dynamic libraries
    sys.path.append(PATH_DYLIBS)

    # Initialize pygame for music playback.
    pygame.init()
    pygame.mixer.init()

    app: MusicPlayerApp = MusicPlayerApp()
    app.run()
