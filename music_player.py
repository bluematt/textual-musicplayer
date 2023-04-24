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
from textual.reactive import Reactive
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Checkbox, Label
from textual.widgets import DataTable, ContentSwitcher, Placeholder, DirectoryTree

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
TRACK_EXT: tuple[str, ...] = (".mp3", ".ogg",
                              # ".mp4",
                              # ".m4a",
                              # ".flac"
                              )

SYM_PLAY: str = "\u25B6"  # ▶️
SYM_PAUSE: str = "\u23F8"  # ⏸️
# SYM_PLAY_PAUSE: str = "\u23EF"  # ⏯️
# SYM_REPEAT: str = "\U0001F501"  # 🔁
# SYM_RANDOM: str = "\U0001F500"  # 🔀
SYM_SPEAKER: str = "\U0001F508"  # 🔈
SYM_SPEAKER_MUTED: str = "\U0001F507"  # 🔇

TRACK_UNKNOWN: str = "<unknown track>"
ARTIST_UNKNOWN: str = "<unknown artist>"
ALBUM_UNKNOWN: str = "<unknown album>"

PLAY: str = "Play"
PAUSE: str = "Pause"
REPEAT: str = "Repeat"
RANDOM: str = "Random"

PATH_HOME: str = "~"
PATH_ROOT: str = "/"

FRAME_RATE: float = 1.0 / 60.0  # Hz


class ProgressBar(Static):
    """A bar that tracks progress."""

    # The multiplier for `percent_complete` to fill up the bar's width.
    PERCENTAGE_MULTIPLIER: float = 100.0

    class ProgressBarTrack(Static):
        """The track inside the `ProgressBar` that tracks progress."""

    percent_complete = Reactive(0.0)

    def compose(self) -> ComposeResult:
        yield self.ProgressBarTrack("", id="progress_bar_track")

    def watch_percent_complete(self):
        """Watch for changes to `percent_complete`."""
        self.update_track_width(self.percent_complete * self.PERCENTAGE_MULTIPLIER)

    def update_track_width(self, width: float):
        """Update the width of the track as a percentage."""
        # TEMP Display the progress as a percentage.
        # self.query_one("#progress_bar_track", self.ProgressBarTrack).update(f"{str(int(width))}%")
        self.query_one("#progress_bar_track", self.ProgressBarTrack).styles.width = f"{str(width)}%"


class TrackProgress(Static):
    """Display information about a track's progress."""

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(format_duration(0.0).rjust(10), id="track_position"),
            ProgressBar(id="progress_bar"),
            Label(format_duration(59999.0).ljust(10), id="track_length")
        )


class TrackInformation(Static):
    """The track information."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(TRACK_UNKNOWN, id="track_name"),
            Static(ARTIST_UNKNOWN, id="artist_name"),
            Static(ALBUM_UNKNOWN, id="album_name"),
            TrackProgress(id="track_progress")
        )


class PlayerControls(Static):
    """The music controls."""

    def compose(self) -> ComposeResult:
        yield Button(PLAY, id="play_button")
        yield Button(PAUSE, id="pause_button")
        yield Checkbox(REPEAT, id="repeat_checkbox")
        yield Checkbox(RANDOM, id="random_checkbox")


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

    title = Reactive("")
    artist = Reactive("")
    album = Reactive("")
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
        yield Static("Loading...", id="status")


def format_duration(duration: float) -> str:
    """Converts a duration in seconds into a minute/second string."""
    (m, s) = divmod(duration, 60.0)
    return f"{int(m)}\u2032{int(s):02}\u2033"  # unicode prime/double prime resp.


def stop_music() -> None:
    """Stop playback."""
    pygame.mixer.init()
    pygame.mixer.music.stop()
    pygame.mixer.music.rewind()
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
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("m", "toggle_mute", "Mute/Unmute"),
        Binding("d", "toggle_dark", "Toggle dark mode", show=False),
        Binding("o", "open_directory", "Open directory"),
        Binding("r", "toggle_repeat", "Toggle repeat", show=False),
        Binding("m", "toggle_random", "Toggle random", show=False),
        Binding("p", "toggle_now_playing", "Now playing"),
        Binding("q", "quit", "Quit", show=False),
        Binding("backslash", "restart_playlist", "Restart playlist", show=False),
        Binding("left_square_bracket", "previous", "Previous track", show=False),
        Binding("right_square_bracket", "next_track", "Next track", show=False),
    ]

    # The current working directory (where music files are).
    cwd = Reactive("./demo_music")

    # The list of available tracks.
    tracks: Reactive[dict[TrackPath, Track]] = Reactive({})

    # The current playlist.
    playlist: Reactive[list[TrackPath]] = Reactive([])

    # The index of the current track.
    current_track_index: Reactive[Optional[int]] = Reactive(0)

    # The index of the previous track.
    previous_track_index: Optional[int] = None

    # The ID of the previous context widget.
    previous_context: str = "tracklist"

    # A timer used to perform time-based updates.
    progress_timer: Timer = None

    def watch_current_track_index(self, previous_track_index: int, new_track_index: int) -> None:
        """Watch for changes to `current_track_index`."""
        self.previous_track_index = previous_track_index
        self.current_track_index = new_track_index

        if self.current_track_index is None:
            self.previous_track_index = None
            self.stop_music()
            return

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

    def get_previous_track_index(self) -> int:
        previous_track_index: int = self.current_track_index - 1
        return previous_track_index if previous_track_index < len(self.playlist) else len(self.playlist) - 1

    def compose(self) -> ComposeResult:
        """Render the music player."""
        yield Header(show_clock=True)
        yield MusicPlayer()
        yield Footer()

    def on_mount(self) -> None:
        """Mount the application."""
        self.refresh_tracks()
        self.focus_playlist()

        self.progress_timer = self.set_interval(FRAME_RATE, self.update_progress, pause=False)
        self.play()

    def play(self) -> None:
        """Play the current track."""
        # If no tracks, no current track.
        if len(self.playlist) <= 0:
            self.current_track_index = None

        # If no current track, bail.
        if self.current_track_index is None:
            return

        track: Track = self.get_track(self.current_track_index)
        self.set_status(f"{SYM_PLAY}  [bold]{track.title}[/] by {track.artist}")
        self.play_track(self.get_track_path(self.current_track_index))

    def update_playlist_datatable(self) -> None:
        """Update the playlist with the tracks from the current working directory."""
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

        # Create the data for the playlist.
        for track_path in self.playlist:
            track: Track = self.tracks[track_path]
            track_row = [None, track.title, track.artist, track.album, track.duration, track.genre]
            track_row[4] = Text(format_duration(track.duration), justify="right")
            playlist.add_row(*track_row, key=track_path)

    def action_toggle_play(self) -> None:
        """Toggle play/pause."""
        pygame.mixer.init()
        if is_playing():
            self.pause()
        else:
            self.unpause()

    def action_toggle_now_playing(self) -> None:
        """Action to toggle the 'now playing' context."""
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
        """Action to toggle repeating."""
        self.query_one("#repeat_checkbox", Checkbox).toggle()

    def action_toggle_random(self) -> None:
        """Action to toggle playlist randomisation."""
        self.query_one("#random_checkbox", Checkbox).toggle()

    def action_open_directory(self) -> None:
        """Action to open the directory_browser."""
        self.set_context("directory_browser")
        self.set_focus(self.query_one("#directory_browser", DirectoryBrowser))
        # TODO Can we highlight the cwd in this context?

    def action_close_directory(self) -> None:
        """Action to close the directory_browser."""
        self.query_one("#context").current = "tracklist"

    def action_restart_playlist(self) -> None:
        self.current_track_index = 0

    def action_previous_track(self) -> None:
        self.current_track_index = self.get_previous_track_index()

    def action_next_track(self) -> None:
        self.current_track_index = self.get_next_track_index()

    def pause(self) -> None:
        """Pause playback."""
        pause()
        track: Track = self.get_track(self.current_track_index)
        self.remove_class("playing")
        self.set_status(f"{SYM_PAUSE}  [bold]{track.title}[/] by {track.artist}")
        self.set_playlist_current_icon(SYM_PAUSE, self.current_track_index, self.previous_track_index)

    def unpause(self) -> None:
        """Unpause playback."""
        unpause()
        track: Track = self.get_track(self.current_track_index)
        self.add_class("playing")
        self.set_status(f"{SYM_PLAY}  [bold]{track.title}[/] by {track.artist}")
        self.set_playlist_current_icon(SYM_PLAY, self.current_track_index, self.previous_track_index)

    def sort_tracks(self) -> None:
        """Sort the tracks according to the current app state."""
        random_checkbox = self.query_one("#random_checkbox", Checkbox)
        if random_checkbox.value:
            shuffle(self.playlist)
        else:
            self.playlist.sort()

    def scan_track_directory(self) -> None:
        """Scan the current working directory for music files."""
        files = get_files_in_directory(self.cwd)
        self.update_tracks_from_files(files)

    def create_playlist(self) -> None:
        """Create a playlist for the currently available tracks."""
        self.playlist = list(self.tracks.keys())
        self.sort_tracks()

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
        self.update_progress()

    def update_track_info(self, title: Optional[str], artist: Optional[str], album: Optional[str]) -> None:
        """Update the UI with details of the current track."""
        self.query_one("#track_name", Static).update(f"[bold]{title}[/]" if title else f"[bold]{TRACK_UNKNOWN}[/]")
        self.query_one("#artist_name", Static).update(f"{artist}" if artist else ARTIST_UNKNOWN)
        self.query_one("#album_name", Static).update(f"[italic]{album}[/]" if album else f"[italic]{ALBUM_UNKNOWN}[/]")

    def play_track(self, track_path: TrackPath) -> None:
        """Play a track."""
        if track_path:
            play_track(track_path, self.get_loops())
            self.add_class("playing")
            self.update_track_info_track(track_path)
            self.set_playlist_current_icon(SYM_PLAY, self.current_track_index, self.previous_track_index)

    def get_loops(self) -> int:
        """Return how many times to loop a track, based on the repeat switch's state."""
        return -1 if self.query_one('#repeat_checkbox', Checkbox).value else 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handler for button presses."""
        if event.button.id == "play_button":
            self.unpause()

        if event.button.id == "pause_button":
            self.pause()

        self.focus_playlist()

    def on_key(self, event: events.Key) -> None:
        """Handler for unhandled key presses."""
        # Save a screenshot to the desktop.
        if event.key == "s":
            self.save_screenshot(path=path.expanduser("~/Desktop"))

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handler for Checkbox changes."""
        if event.checkbox.id == "random_checkbox":
            current_track_path: TrackPath = self.get_track_path(self.current_track_index)
            self.sort_tracks()
            self.update_playlist_datatable()
            self.current_track_index = self.playlist.index(current_track_path)

        # TODO Implement repeat.
        if event.checkbox.id == "repeat_checkbox":
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

        self.stop_music()

        self.cwd = event.directory
        self.refresh_tracks()
        self.focus_playlist()

        self.previous_track_index = None
        self.current_track_index = 0
        self.play()

    def stop_music(self) -> None:
        """Stop the music."""
        self.remove_class("playing")
        self.set_status(f"Stopped")
        self.update_track_info(None, None, None)
        self.update_progress()
        stop_music()

    def update_progress(self) -> None:
        """Keep track of what's happening."""
        progress_in_s: float = 0.0
        track_length_in_s: float = 0.0
        progress: float = 0.0

        # Update track progress if we have a track.
        if self.current_track_index is not None:
            track_length_in_s, progress_in_s = self.get_track_progress()
            progress = (progress_in_s / track_length_in_s)

        # Has the track finished?
        # pygame.mixer.music.get_pos() can return -0.01 if pygame detects that the track has finished playing.
        if progress_in_s < 0.0 or progress >= 1.0:
            self.advance_to_next_track()

        self.query_one("#progress_bar", ProgressBar).percent_complete = progress
        self.query_one("#track_position", Static).update(format_duration(progress_in_s))
        self.query_one("#track_length", Static).update(format_duration(track_length_in_s))

    def get_track_progress(self) -> tuple[float, float]:
        pygame.mixer.init()
        track: Track = self.get_track(self.current_track_index)
        track_length_in_s: float = track.duration
        # get_pos() returns a value in milliseconds
        progress_in_s = float(pygame.mixer.music.get_pos()) / 1000.0

        return track_length_in_s, progress_in_s

    def get_track_path(self, index: int) -> str:
        return self.playlist[index]

    def get_track(self, index: int) -> Track:
        return self.tracks[self.get_track_path(index)]

    def advance_to_next_track(self):
        self.set_status("Next track...")
        self.current_track_index = self.get_next_track_index()

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

    def refresh_tracks(self) -> None:
        """Refresh the track list and regenerate playlists."""
        self.set_status("Refreshing playlist...")
        self.previous_track_index = None
        self.scan_track_directory()
        self.create_playlist()
        self.update_playlist_datatable()

    def set_status(self, message: str):
        self.query_one('#status', Static).update(message)


if __name__ == "__main__":
    # Add path to the dynamic libraries
    # TODO Is this actually required, or are libraries already on the path?
    sys.path.append(PATH_DYLIBS)

    # Initialize pygame for music playback.
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0)

    app: MusicPlayerApp = MusicPlayerApp()
    app.run()
