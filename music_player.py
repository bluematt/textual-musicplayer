from __future__ import annotations

import sys

from os import walk, path, environ
from pathlib import Path
from random import shuffle
from typing import ClassVar, Iterable, Optional

from tinytag import TinyTag
from tinytag.tinytag import ID3, Ogg, Wave, Flac, Wma, MP4, Aiff

from rich.text import Text  # noqa - required by textual
from rich.console import RenderableType  # noqa - required by textual

from textual import log, events
from textual.coordinate import Coordinate
from textual.timer import Timer
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive, Reactive
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Horizontal, Center, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Switch
from textual.widgets import Label, DataTable, ContentSwitcher, Placeholder, DirectoryTree

# Hide the Pygame prompts from the terminal.
# Imported libraries should *not* dump to the terminal...
# See https://github.com/pygame/pygame/issues/1468
# This may show as a warning in IDEs that support PEP 8 (E402) that don't support 'noqa'.
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "True"
import pygame  # noqa: E402

Track = TinyTag | ID3 | Ogg | Wave | Flac | Wma | MP4 | Aiff
TrackPath = str

# Path to binaries.
PATH_DYLIBS: str = "./venv/lib/python3.7/site-packages/pygame/.dylibs"

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

PATH_HOME: str = "~"
PATH_ROOT: str = "/"


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


class ProgressBar(Static):
    """A bar that tracks progress."""

    # The multiplier for `percent_complete` to fill up the bar's width.
    # TODO Tweak this to fill it up properly, based on the TODO in `ProgressBarTrack`.
    MAX_MULTIPLIER: float = 100.0

    class ProgressBarTrack(Static):
        """The track inside the `ProgressBar` that tracks progress."""
        # TODO There seems to be a bug where the width is about 80-90% of
        #      the parent at 100% width.

    percent_complete = Reactive(0.0)

    def compose(self) -> ComposeResult:
        yield self.ProgressBarTrack(id="progress_bar_track")

    def watch_percent_complete(self):
        """Watch for changes to `percent_complete`."""
        self.update_track_width(self.percent_complete * self.MAX_MULTIPLIER)

    def update_track_width(self, width: float):
        """Update the width of the track as a percentage."""
        self.query_one("#progress_bar_track", self.ProgressBarTrack).styles.width = f"{width}%"


class TrackInformation(Static):
    """The track information."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            TitleInfo(LBL_TRACK_UNKNOWN, id="track_name"),
            ArtistInfo(LBL_ARTIST_UNKNOWN, id="artist_name"),
            AlbumInfo(LBL_ALBUM_UNKNOWN, id="album_name"),
            ProgressBar(id="progress_bar")
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
                Switch(value=False, id="random_switch"),
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
        Binding("~", "home", "Home directory"),
        Binding("/", "root", "Root directory"),
        Binding("o", "close_browser", "Close"),
    ]

    class DirectorySelected(Message):
        directory: str

        def __init__(self, directory: str):
            self.directory = directory
            super().__init__()

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter paths to non-hidden directories only."""
        return [p for p in paths if p.is_dir() and not p.name.startswith(".")]

    def on_tree_node_selected(self, event: DirectoryBrowser.NodeSelected) -> None:
        """Handler for selecting a directory in the directory browser."""
        self.post_message(self.DirectorySelected(event.node.data.path))

    def action_home(self) -> None:
        """Set the root of the directory browser to `~`."""
        self.parent.refresh_directory_browser(PATH_HOME)

    def action_root(self) -> None:
        """Set the root of the directory browser to `/`."""
        self.parent.refresh_directory_browser(PATH_ROOT)

    def action_close_browser(self) -> None:
        """Close the directory browser and show the playlist."""
        self.app.focus_playlist()


class NowPlaying(Placeholder):
    """Display what is currently playing."""
    BINDINGS = []

    title: reactive[str] = reactive("")
    artist: reactive[str] = reactive("")
    album: reactive[str] = reactive("")
    artwork = None


class ContextSwitcher(ContentSwitcher):

    def compose(self) -> ComposeResult:
        yield TrackList(id="tracklist")
        yield self.new_directory_browser(PATH_HOME)
        yield NowPlaying(id="now_playing")

    def new_directory_browser(self, base_path: str) -> DirectoryBrowser:  # noqa
        return DirectoryBrowser(path=path.expanduser(base_path), id="directory_browser")

    def refresh_directory_browser(self, base_path: str):
        self.query_one("#directory_browser", DirectoryBrowser).remove()
        self.mount(self.new_directory_browser(base_path))
        self.query_one("#directory_browser", DirectoryBrowser).focus()


class MusicPlayer(Static):
    """The main music player user interface."""

    def compose(self) -> ComposeResult:
        yield TrackInformation()
        yield PlayerControls()
        yield ContextSwitcher(id="context", initial="tracklist")


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


def play_track(track_path: TrackPath, loops: int = -1) -> None:
    """Play a track."""
    if not track_path:
        log("NO TRACK TO PLAY")
        return

    pygame.mixer.init()
    pygame.mixer.music.load(track_path)
    pygame.mixer.music.rewind()  # We need this to get accurate timings.
    pygame.mixer.music.play(loops=loops)


def queue_track(track_path: TrackPath = None, loops: int = -1) -> None:
    """Queue a track for playback when the current track finishes."""
    if not track_path:
        log("NO TRACK TO QUEUE")
        return

    pygame.mixer.init()
    pygame.mixer.music.queue(track_path, loops=loops)


def get_files_in_directory(directory: str) -> list[TrackPath]:
    """Returns the (sorted) list of files in the directory."""
    if not path.exists(directory) or not path.isdir(directory):
        raise FileNotFoundError

    files = [
        TrackPath(path.join(dir_path, f))
        for (dir_path, _dir_names, filenames) in walk(directory)
        for f in filenames if f.endswith(TRACK_EXT) and not f.startswith(".")
    ]

    files.sort()

    return files


class MusicPlayerApp(App):
    """A music player app."""

    TITLE = "tTunes"  # 😏

    CSS_PATH: ClassVar[CSSPathType | None] = "music_player.css"

    BINDINGS = [
        Binding("space", "toggle_play", SYM_PLAY_PAUSE),
        Binding("m", "toggle_mute", "Mute/Unmute"),
        Binding("d", "toggle_dark", "Toggle dark mode"),
        Binding("o", "open_directory", "Open directory"),
        Binding("r", "toggle_repeat", "Toggle repeat", show=False),
        Binding("m", "toggle_random", "Toggle random", show=False),
        Binding("p", "toggle_now_playing", "Now playing"),
        Binding("q", "quit", "Quit", show=False),
    ]

    # The current working directory (where music files are).
    cwd = Reactive("./demo_music")

    # The list of available tracks.
    tracks: Reactive[dict[TrackPath, Track]] = Reactive({})

    # The current playlist.
    playlist: Reactive[list[TrackPath]] = Reactive([])

    # The index of the current track.
    current_track_index = Reactive(0)

    # The index of the previous track.
    previous_track_index: int = None

    # The ID of the previous context widget.
    previous_context: str = "tracklist"

    # A timer used to perform time-based updates.
    progress_timer: Timer = None

    def watch_cwd(self, previous_cwd: str, new_cwd: str) -> None:
        """Watch for changes to `cwd`."""
        if previous_cwd != new_cwd:
            log("CWD CHANGED")
            # self.scan_track_directory()

    # def watch_tracks(self) -> None:
    #     """Watch for changes to `tracks`."""
    #     log("PLAYLIST UPDATED")
    #     self.update_track_list()

    def watch_current_track_index(self, previous_track_index: int, _new_track_index: int) -> None:
        """Watch for changes to `current_track_index`."""
        self.previous_track_index = previous_track_index
        if is_playing():
            self.play()

    def set_playlist_current_icon(self, icon: str, row: int, previous_row: int = None) -> None:
        """Set the icon for the currently playing track in the playlist."""
        playlist: DataTable = self.get_playlist()
        if previous_row is not None:
            playlist.update_cell_at(Coordinate(row=previous_row, column=0), "")
        playlist.update_cell_at(Coordinate(row=row, column=0), icon)

    def get_next_track_index(self) -> int:
        next_track_index: int = self.current_track_index + 1
        return next_track_index if next_track_index < len(self.playlist) else 0

    def compose(self) -> ComposeResult:
        """Render the music player."""
        yield Header(show_clock=True)
        yield MusicPlayer()
        yield Footer()

    def on_mount(self) -> None:
        """Mount the application."""
        # Scan for music in the current working directory.
        self.refresh_tracks()

        self.focus_playlist()

        self.progress_timer = self.set_interval(1 / 30, self.update_progress_bar, pause=False)

        # Set the current track to be the first track in the playlist.
        self.play()

    def play(self):
        """Play the current track."""
        if len(self.playlist) <= 0:
            self.current_track_index = 0
            self.stop_music()
            return

        current_track_index: int = self.current_track_index
        next_track_index: int = self.get_next_track_index()

        self.play_track(self.playlist[current_track_index])
        self.queue_track(self.playlist[next_track_index])

    def update_playlist_datatable(self) -> None:
        """Update the playlist with the tracks from the current working directory."""

        # Create the visual data for the playlist.
        playlist_data = []
        for track_path in self.playlist:
            track: Track = self.tracks[track_path]
            track_row = [None, track.title, track.artist, track.album, track.duration, track.genre]
            track_row[4] = Text(format_duration(track.duration), justify="right")
            playlist_data.append(track_row)

        playlist: DataTable = self.get_playlist()
        playlist.clear(columns=True)
        # TODO See if there is a way to expand a DataTable to full width.
        #      See: https://github.com/Textualize/textual/discussions/1942
        # TODO This can probably be optimised by laying out the shape
        #      of the grid in advance, and just refilling the data.
        playlist.add_column(label=" ", width=1, key="status")
        playlist.add_column(label="Title")
        playlist.add_column(label="Artist")
        playlist.add_column(label="Album")
        playlist.add_column(label="Length")
        playlist.add_column(label="Genre")
        playlist.add_rows(playlist_data)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_toggle_play(self) -> None:
        """Toggle play/pause."""
        pygame.mixer.init()
        if is_playing():
            self.pause()
        else:
            self.unpause()

    def pause(self):
        """Pause playback."""
        pause()
        self.set_playlist_current_icon(SYM_PAUSE, self.current_track_index, self.previous_track_index)

    def unpause(self):
        """Unpause playback."""
        unpause()
        self.set_playlist_current_icon(SYM_PLAY, self.current_track_index, self.previous_track_index)

    def action_toggle_now_playing(self) -> None:
        """Toggle the 'now playing' context."""
        current_context: str = self.query_one("#context", ContentSwitcher).current
        if current_context == "now_playing":
            self.query_one("#context", ContentSwitcher).current = self.previous_context
        else:
            self.previous_context = current_context
            self.query_one("#context", ContentSwitcher).current = "now_playing"

    def action_toggle_mute(self) -> None:
        """Action to toggle muting."""
        toggle_mute()

    def action_toggle_repeat(self) -> None:
        """Toggle repeating."""
        repeat_switch = self.query_one("#repeat_switch", Switch)
        repeat_switch.toggle()

    def action_toggle_random(self) -> None:
        """Toggle playlist randomisation."""
        random_switch = self.query_one("#random_switch", Switch)
        random_switch.toggle()

    def sort_tracks(self):
        """Sort the tracks according to the current app state."""
        random_switch = self.query_one("#random_switch", Switch)
        if random_switch.value:
            shuffle(self.playlist)
        else:
            self.playlist.sort()

    def action_open_directory(self) -> None:
        """Open the directory_browser."""
        self.set_context("directory_browser")
        self.set_focus(self.query_one("#directory_browser", DirectoryBrowser))

    def action_close_directory(self) -> None:
        """Close the directory_browser."""
        self.query_one("#context").current = "tracklist"

    def scan_track_directory(self) -> None:
        """Scan the current working directory for music files."""
        files = get_files_in_directory(self.cwd)
        self.update_tracks_from_files(files)

    def create_playlist(self) -> None:
        """Create a playlist for the currently available tracks."""
        self.playlist = list(self.tracks.keys())

    def update_tracks_from_files(self, files: list) -> None:
        # Get track metadata from music files.
        tracks: list[Track] = [TinyTag.get(f) for f in files]

        # Clear the existing list of tracks and create a new {TrackPath:Track} mapping.
        self.tracks.clear()
        [self.tracks.update({TrackPath(files[idx]): track}) for idx, track in enumerate(tracks)]

    def update_track_info_track(self, track_path: TrackPath) -> None:
        """Update track info with a track's info."""
        track: Track = self.tracks[track_path]
        self.update_track_info(track.title, track.artist, track.album)

    def update_track_info(self, title: Optional[str], artist: Optional[str], album: Optional[str]):
        """Update the UI with details of the current track."""
        self.query_one("#track_name").title = title
        self.query_one("#artist_name").artist = artist
        self.query_one("#album_name").album = album

    def play_track(self, track_path: TrackPath) -> None:
        """Play a track."""
        if is_playing():
            self.stop_music()

        if track_path:
            play_track(track_path, self.get_loops())
            self.update_track_info_track(track_path)
            self.set_playlist_current_icon(SYM_PLAY, self.current_track_index, self.previous_track_index)

    def queue_track(self, track_path: TrackPath) -> None:
        if track_path:
            queue_track(track_path)

    def get_loops(self) -> int:
        """Return how many times to loop a track, based on the repeat switch's state."""
        return -1 if self.query_one('#repeat_switch', Switch).value else 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handler for button presses."""
        if event.button.id == "play_button":
            unpause()

        if event.button.id == "pause_button":
            pause()

        self.focus_playlist()

    def on_key(self, event: events.Key) -> None:
        """Handler for unhandled key presses."""
        # Save a screenshot to the desktop.
        if event.key == "s":
            self.save_screenshot(path=path.expanduser("~/Desktop"))

    def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handler for switch changes."""
        pass

        if event.switch.id == "random_switch":
            self.sort_tracks()
            self.update_playlist_datatable()

        # TODO Implement repeat.
        if event.switch.id == "repeat_switch":
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler for selecting a row in the data table."""
        self.current_track_index = event.cursor_row

    def on_directory_browser_directory_selected(self, event: DirectoryBrowser.DirectorySelected) -> None:
        """Handler for selecting a directory in the directory browser."""
        files = get_files_in_directory(event.directory)
        if len(files) <= 0:
            log(f"NO USABLE FILES IN DIRECTORY {event.directory}")
            return

        was_playing: bool = is_playing()

        if was_playing:
            self.stop_music()

        self.set_working_directory(event.directory)
        self.refresh_tracks()
        self.focus_playlist()

        self.current_track_index = 0

    def stop_music(self):
        """Stop the music."""
        self.update_track_info(None, None, None)
        stop_music()

    def update_progress_bar(self) -> None:
        """Update the progress bar with the percentage of the track played."""
        progress = 0.0

        if self.current_track_index:
            track: Track = self.tracks[self.playlist[self.current_track_index]]
            track_length_in_s: float = track.duration

            pygame.mixer.init()
            progress_in_s: float = float(pygame.mixer.music.get_pos()) / 1000.0

            progress: float = (progress_in_s / track_length_in_s)

        self.query_one("#progress_bar", ProgressBar).percent_complete = progress

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

    def refresh_tracks(self):
        self.scan_track_directory()
        self.create_playlist()
        self.update_playlist_datatable()


if __name__ == "__main__":
    # Add path to the dynamic libraries
    sys.path.append(PATH_DYLIBS)

    # Initialize pygame for music playback.
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0)

    app: MusicPlayerApp = MusicPlayerApp()
    app.run()
