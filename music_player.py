"""A simple music player (MP3, etc.) using [Textual](https://textual.textualize.io/)."""

from __future__ import annotations

from io import BytesIO
from os import environ, path, walk
from os.path import abspath
from pathlib import Path
from random import shuffle
from typing import Iterable, Optional
from collections import deque

from tinytag import TinyTag

from rich.text import Text
from rich_pixels import Pixels

from PIL import Image

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.coordinate import Coordinate
from textual.reactive import Reactive
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import Button, DataTable, DirectoryTree, Footer, Header, Input, Placeholder, ProgressBar
from textual.widgets import Static
from textual.widgets._data_table import RowKey  # noqa - required to extend DataTable
from textual.widgets._directory_tree import DirEntry  # noqa - required to extend DirectoryTree

# Hide the Pygame prompts from the terminal.
# Imported libraries should *not* dump to the terminal...
# See https://github.com/pygame/pygame/issues/1468
# This may show as a warning in IDEs that support PEP 8 (E402) that don't support 'noqa'.
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "True"
import pygame  # noqa: E402

TrackPath = str

# Path to binaries.
PATH_DYLIBS: str = "./venv/lib/python3.7/site-packages/pygame/.dylibs"

# The supported file types.
# TODO Determine while audio file types are/can be supported.
TRACK_EXT: tuple[str, ...] = (".mp3", ".ogg",)  # ".mp4",  ".m4a", ".flac" - currently unsupported

# Localisation.
TRACK_UNKNOWN: str = "<unknown track>"
ARTIST_UNKNOWN: str = "<unknown artist>"
ALBUM_UNKNOWN: str = "<unknown album>"
NO_ARTWORK: str = "<no embedded album art>"

# How often the UI is updated.
FRAME_RATE: float = 1.0 / 30.0  # 30 Hz

# Artwork size
ARTWORK_DIMENSIONS: tuple[int, int] = (24, 24)


class Track:
    """Convenience decorator for `TinyTag`."""
    track: TinyTag

    def __init__(self, track: TinyTag):
        self.track = track

    @property
    def title(self) -> str:
        """Return the track's title or a sane default."""
        return stripped_value_or_default(self.track.title, TRACK_UNKNOWN)

    @property
    def artist(self) -> str:
        """Return the track's artist or a sane default."""
        return stripped_value_or_default(self.track.artist, ARTIST_UNKNOWN)

    @property
    def album(self) -> str:
        """Return the track's album title or a sane default."""
        return stripped_value_or_default(self.track.album, ALBUM_UNKNOWN)

    @property
    def genre(self):
        """Return the track's genre."""
        return self.track.genre

    @property
    def duration(self):
        """Return the track's duration."""
        return self.track.duration

    @property
    def image(self) -> Pixels | str:
        """Return the track's image, if available."""
        image_data = self.track.get_image()
        if image_data:
            image: Image = Image.open(BytesIO(image_data))
            return Pixels.from_image(image.resize(size=ARTWORK_DIMENSIONS))
        return NO_ARTWORK

    def contains(self, filter_str: str):
        """Return whether `filter_str` (or part thereof) is (naïvely) somewhere within the track's information."""
        filters = filter_str.lower().split(" ")
        search = f"{self.title} {self.artist} {self.album} {self.genre}".lower()
        return all(f in search for f in filters)

    def __repr__(self):
        return f"{self.title} by {self.artist}"


class TrackProgress(Static):
    """Display the progress of a track."""

    def compose(self) -> ComposeResult:
        yield Static(format_duration(0.0), id="track_current_time")
        yield ProgressBar(total=None, show_eta=False, show_percentage=False, id="progress_bar")
        yield Static(format_duration(0.0), id="track_total_time")


class TrackInformation(Static):
    """Display information about a track."""

    def compose(self) -> ComposeResult:
        yield Static(TRACK_UNKNOWN, id="title")
        yield Static(ARTIST_UNKNOWN, id="artist")
        yield Static(ALBUM_UNKNOWN, id="album")
        yield TrackProgress()


class PlayerControls(Static):
    """Playback controls."""

    def compose(self) -> ComposeResult:
        yield Button("|<", id="previous_track")
        yield Button("|>", id="play")
        yield Button("||", id="pause")
        yield Button(">|", id="next_track")


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


class Browser(DirectoryTree):
    def on_tree_node_selected(self, event: DirectoryTree.NodeSelected):
        self.app.query_one(DirectoryBrowser).directory = event.node.data

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter paths to non-hidden directories only."""
        return [p for p in paths if p.is_dir() and not p.name.startswith(".")]


class DirectoryControls(Static):
    def compose(self) -> ComposeResult:
        yield Button("Select", id="directory_select")
        yield Button("Cancel", id="directory_cancel")


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


class AlbumArtwork(Static):
    """Container for album artwork."""

    def compose(self) -> ComposeResult:
        yield Static(NO_ARTWORK, id="album_artwork")


class SongControlBar(Static):
    """The song control bar."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            PlayerControls(id="playback_controls"),
            Static("󰒞", id="playback_status")
        )
        yield TrackInformation(id="song_information")
        yield FilterInput("", placeholder="Filter", id="filter")


class NowPlayingScreen(Screen):
    """Screen that displays the currently playing track and album artwork."""
    BINDINGS = [
        Binding("space", "app.play_pause", "|>/||"),
        Binding("left_square_bracket", "app.previous_track", "<<"),
        Binding("right_square_bracket", "app.next_track", ">>"),
        Binding("p", "app.pop_screen()", "Tracks"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield AlbumArtwork()
        yield Vertical(
            TrackInformation(id="song_information"),
            PlayerControls(id="playback_controls"),
            Static("󰒞", id="playback_status")
        )
        # yield Static("", id="status_bar", disabled=True)
        yield Footer()


class MusicPlayer(Static):
    def compose(self) -> ComposeResult:
        yield SongControlBar(id="song_control_bar")
        yield TrackList(id="track_list")
        yield Static("", id="status_bar")


def stripped_value_or_default(value: any, default: str) -> str:
    """Return a value (left and right trimmed) or a default, if it would be an empty string."""
    if not (value and str(value).strip()):
        return default
    return str(value).strip(" ")


def get_files_in_directory(directory: str) -> list[str]:
    """Return the selected media files (sorted) in the directory tree starting at `directory`."""
    if not path.exists(directory) or not path.isdir(directory):
        raise NotADirectoryError

    files = [
        TrackPath(path.join(dir_path, file))
        for (dir_path, _dir_names, filenames) in walk(directory)
        for file in filenames if file.endswith(TRACK_EXT) and not file.startswith(".")
    ]

    if len(files) == 0:
        raise FileNotFoundError

    files.sort()
    return files


def format_duration(duration: float) -> str:
    """Convert a duration in seconds into a minute/second string."""
    (m, s) = divmod(duration, 60.0)
    return f"{int(m)}\u2032{int(s):02}\u2033"  # unicode prime/double prime resp.


def init_pygame() -> None:
    """Initialise pygame for playback."""
    pygame.init()
    pygame.mixer.init()


def play_track(track_path: TrackPath) -> None:
    """Load media and start playback."""
    pygame.mixer.music.load(track_path)
    pygame.mixer.music.rewind()
    pygame.mixer.music.play(-1)


def unpause_playback() -> None:
    """Unpause playback."""
    pygame.mixer.music.unpause()


def pause_playback() -> None:
    """Pause playback."""
    pygame.mixer.music.pause()


def stop_playback() -> None:
    """Stop playback and unload the loaded media."""
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()


def get_playback_position() -> float:
    """Return the current playback position, in seconds."""
    return float(pygame.mixer.music.get_pos()) / 1000.0  # get_pos() returns a value in milliseconds


class TrackScreen(Screen):
    """Screen that displays the track list."""

    BINDINGS = [
        Binding("space", "app.play_pause", "|>/||"),
        Binding("left_square_bracket", "app.previous_track", "<<"),
        Binding("right_square_bracket", "app.next_track", ">>"),
        Binding("p", "app.push_screen('now_playing')", "Now playing"),
        Binding("ctrl+f", "focus_filter", "Filter"),
        Binding("ctrl+x", "clear_filter", "Clear filter", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MusicPlayer()
        yield Footer()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_clear_filter(self):
        self.query_one("#filter", Input).value = ""
        self.app.filter_playlist()


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


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("f1", "pop_screen()", "Close help"),
        Binding("escape", "pop_screen()", "Close help", show=False),
    ]

    def compose(self) -> ComposeResult:
        # TODO load help information from "HELP.md".
        yield Placeholder("TODO Help information will go here...")


class MusicPlayerApp(App):
    """A music player app."""

    TITLE = "tTunes"  # 😏

    CSS_PATH = "music_player.css"

    BINDINGS = [
        Binding("f1", "push_screen('help')", "Help"),
        Binding("o", "push_screen('browser')", "Music browser"),
        Binding("q", "stop_playback", "Stop"),
        Binding("r", "toggle_shuffle", "Toggle shuffle", show=False),
        Binding("s", "save_screen", "Save screenshot", show=False),
    ]

    SCREENS = {
        "help": HelpScreen(),
        "browser": BrowserScreen(),
        "tracks": TrackScreen(),
        "now_playing": NowPlayingScreen()
    }

    # The current working directory (location of music files).
    cwd = Reactive(".")
    # The currently available tracks, loaded from `cwd`.
    tracks: Reactive[dict[TrackPath, Track]] = Reactive({})
    # The current order of the tracks to play.
    playlist: Reactive[deque[TrackPath]] = Reactive(deque())
    # The index of the current track in `playlist`.
    current_track: Reactive[TrackPath] = Reactive("")
    # Timer to keep track of track progress.
    progress_timer: Timer = None

    def watch_cwd(self) -> None:
        self.refresh_tracks(self.cwd)

    def watch_current_track(self) -> None:
        if self.is_playing:
            self.play()

    def watch_playlist(self) -> None:
        self.update_track_list()

    async def on_mount(self) -> None:
        await self.push_screen("tracks")
        self.set_status("Starting up...")
        self.progress_timer = self.set_interval(FRAME_RATE, self.monitor_track_progress, pause=False)
        self.stop()
        self.refresh_tracks(self.cwd)
        self.reset_current_track()

    def action_save_screen(self) -> None:
        self.save_screenshot(path=path.expanduser("~/Desktop"))

    def action_play_pause(self) -> None:
        self.toggle_playback()

    def action_toggle_shuffle(self) -> None:
        self.toggle_class("shuffled")
        if self.has_class("shuffled"):
            self.shuffle_playlist()
            self.set_status("Playlist shuffle: on")
            [widget.update("󰒟") for widget in self.query("#playback_status").results()]
        else:
            self.unshuffle_playlist()
            self.set_status("Playlist shuffle: off")
            [widget.update("󰒞") for widget in self.query("#playback_status").results()]

    def action_next_track(self) -> None:
        self.select_next_track()

    def action_previous_track(self) -> None:
        self.select_previous_track()

    def reset_current_track(self):
        """Reset the current track to the first in the playlist."""
        self.current_track = self.playlist[0]

    def filter_playlist(self, filter_str: str = ""):
        """Filter the playlist by the supplied filter."""
        self.set_status("Filtering track list...")

        filter_str = filter_str.strip()

        if filter_str == "":
            self.set_status("Filtering removed")
            self.reset_playlist()
        else:
            self.set_status(f"Filter track list: '{filter_str}'")
            self.apply_filter_to_playlist(filter_str)

    def select_current_playing_track(self) -> None:
        """Attempt to (re)select the current playing track in the track list."""
        can_highlight: bool = self.highlight_current_track()
        if can_highlight:
            self.select_track(self.current_track)
            self.remove_all_playlist_icons()
            self.set_playlist_icon(self.current_track, "|>" if self.is_playing else "||" if self.is_paused else "")

        self.get_track_list_widget().focus()

    def apply_filter_to_playlist(self, filter_str: str) -> None:
        """Apply filter(s) to the playlist."""
        track_path: TrackPath
        track: Track
        tracks: dict[TrackPath, Track] = dict((track_path, track)
                                              for track_path, track in self.tracks.items()
                                              if track.contains(filter_str) or filter_str in track_path)
        self.update_playlist(list(tracks.keys()))
        self.update_track_list()

    def refresh_tracks(self, track_directory: str) -> None:
        """Refresh the track list from the supplied directory."""
        self.set_status("Loading track list...")
        try:
            files = get_files_in_directory(track_directory)
            self.set_tracks(files)
            self.reset_playlist()
            self.reset_current_track()
        except NotADirectoryError:
            self.set_status(f"{track_directory} is not a directory")
            return
        except FileNotFoundError:
            self.set_status(f"{track_directory} does not contain music")
            return

    def reset_playlist(self):
        """Reset the playlist based on the available tracks."""
        self.update_playlist(self.tracks.keys())
        self.update_track_list()

    def set_tracks(self, files: list[str]) -> None:
        """Set the list of available tracks from the list of files."""
        tracks: list[Track] = [Track(TinyTag.get(file, image=True)) for file in files]
        self.tracks.clear()
        [self.tracks.update({TrackPath(files[idx]): track}) for idx, track in enumerate(tracks)]

    def update_playlist(self, track_paths: list[TrackPath]) -> None:
        """Update the playlist by recreating it from track_path as a new deque."""
        self.playlist = deque(track_paths)

    def shuffle_playlist(self):
        """Randomise the playlist."""
        new_playlist: list[TrackPath] = list(self.playlist)
        shuffle(new_playlist)
        self.update_playlist(new_playlist)

    def unshuffle_playlist(self):
        """Sort the playlist by track path."""
        new_playlist: list[TrackPath] = list(self.playlist)
        new_playlist.sort()
        self.update_playlist(new_playlist)

    def update_track_list(self) -> None:
        """Update the track list with the current playlist."""
        self.set_status("Updating track list...")
        self.get_screen("tracks").query_one(TrackList).update_tracks(self.tracks, self.playlist)
        self.set_status("Track list updated")
        self.select_current_playing_track()

    def toggle_playback(self) -> None:
        """Toggle playback."""
        if self.is_paused or self.is_stopped:
            self.play()
        else:
            self.pause()

    def select_track(self, track_path: TrackPath) -> None:
        """Select the current track from the playlist by advancing the deque to the appropriate index."""
        # TODO Check whether the correct track is selected.
        if self.current_track != track_path:
            previous_track_index = self.get_track_list_widget().get_row_index_from_row_key(self.current_track)
            new_track_index = self.get_track_list_widget().get_row_index_from_row_key(RowKey(track_path))
            self.advance_track(previous_track_index - new_track_index)

    @on(Button.Pressed, "#next_track")
    def select_next_track(self) -> None:
        self.set_status("Skipping...")
        self.advance_track(-1)

    @on(Button.Pressed, "#previous_track")
    def select_previous_track(self) -> None:
        self.set_status("Skipping back...")
        self.advance_track(1)

    def open_directory(self, directory: DirEntry) -> None:
        """Open a directory for reading audio tracks."""
        if directory.path.is_dir():
            self.cwd = path.expanduser(directory.path)
        else:
            self.set_status(f"{directory.path} is not a directory")

    def advance_track(self, by_track_count: int) -> None:
        """Advance to the next track in the playlist."""
        self.stop_if_paused()
        self.playlist.rotate(by_track_count)
        self.reset_current_track()
        self.highlight_current_track()

        track: Track = self.get_current_track()
        self.set_current_track_information(track.title, track.artist, track.album, track.image)
        self.set_current_track_progress(0.0, track.duration)

    def stop_if_paused(self) -> None:
        """Stop playback if playback is paused."""
        if self.is_paused:
            self.stop()

    def highlight_current_track(self) -> bool:
        """Highlight the current track in the track list.  Return whether this was successful."""
        row_index: int = self.get_track_list_widget().get_row_index_from_row_key(self.current_track)
        if row_index is not None:
            self.get_track_list_widget().cursor_coordinate = Coordinate(row=row_index, column=0)
            return True
        return False

    def update_track_information(self) -> None:
        """Update track information."""
        track: Track = self.get_current_track()
        self.set_current_track_information(track.title, track.artist, track.album, track.image)
        self.set_current_track_progress(total=track.duration)

    def monitor_track_progress(self) -> None:
        """
        Keep the track information in the UI up to date.

        NOTE: We have to be careful here as a track that is not yet playing will report a time
        of -0.01 (ms), which is also used to determine when the end of a track has played.
        This isn't ideal, but is the only way that we can get a signal from pygame that
        the current track has finished playing-trying to play beyond the end of the track and
        comparing the duration is not reliable.
        """
        self.update_track_information()

        if self.is_playing or self.is_paused:
            progress: float = get_playback_position()
            track: Track = self.get_current_track()
            self.set_current_track_progress(progress=progress)
            if progress < 0 or progress >= track.duration:
                self.select_next_track()

    def action_stop_playback(self) -> None:
        """Respond to an action to stop playback."""
        self.stop()

    @on(Button.Pressed, "#play")
    def play(self) -> None:
        """Start or resume playback."""
        track: Track = self.get_current_track()
        self.set_status(f"[bold]|> {track.title}[/] by {track.artist}")
        self.add_class("playing")
        self.remove_all_playlist_icons()
        self.set_playlist_icon(self.current_track, "|>")
        self.highlight_current_track()

        if self.is_paused:
            self.remove_class("paused")
            unpause_playback()
        else:
            play_track(self.current_track)

        self.progress_timer.resume()

    @on(Button.Pressed, "#pause")
    def pause(self) -> None:
        """Pause playback."""
        track: Track = self.get_current_track()
        self.set_status(f"[bold]|| {track.title}[/] by {track.artist}")
        self.add_class("paused")
        self.remove_all_playlist_icons()
        self.set_playlist_icon(self.current_track, "||")
        self.progress_timer.pause()

        pause_playback()

    def stop(self) -> None:
        """Stop playback."""
        self.set_status("Idle")
        self.remove_class("playing")
        self.remove_class("paused")
        self.remove_all_playlist_icons()
        self.set_current_track_progress(progress=0.0)
        self.progress_timer.pause()

        stop_playback()

    def set_current_track_information(self, title: str, artist: str, album: str, album_artwork: Pixels | str):
        """Update the current track information."""
        [widget.update(f"[bold]{title}[/]") for widget in self.query("#title")]
        [widget.update(artist) for widget in self.query("#artist")]
        [widget.update(f"[italic]{album}[/]") for widget in self.query("#album")]
        [widget.update(album_artwork) for widget in self.query("#album_artwork")]

    def set_current_track_progress(self, progress: Optional[float] = None, total: Optional[float] = None):
        """Update the progress bar with the current track progress."""
        if progress is not None:
            [widget.update(progress=progress) for widget in self.query("#progress_bar").results()]
            [widget.update(format_duration(progress)) for widget in self.query("#track_current_time").results()]
        if total is not None:
            [widget.update(total=total) for widget in self.query("#progress_bar").results()]
            [widget.update(format_duration(total)) for widget in self.query("#track_total_time").results()]

    def remove_all_playlist_icons(self) -> None:
        """Remove all playlist icons."""
        self.get_track_list_widget().remove_icons()

    def set_playlist_icon(self, track_path: TrackPath, icon: str = "") -> None:
        """Set the playlist `icon` for the track at `track_path`."""
        self.get_track_list_widget().set_icon(track_path, icon)

    def get_track_list_widget(self) -> TrackList:
        """Return the `TrackList` widget on the `TrackScreen` screen."""
        return self.get_screen("tracks").query_one(TrackList)

    @property
    def is_playing(self) -> bool:
        """Return whether the music is currently playing."""
        return self.has_class("playing")

    @property
    def is_paused(self) -> bool:
        """Return whether the music is currently paused."""
        return self.has_class("paused")

    @property
    def is_stopped(self) -> bool:
        """Return whether the music is currently stopped."""
        return not self.has_class("playing")

    def get_current_track(self) -> Track:
        """Return the current `Track`."""
        return self.tracks[self.current_track]

    def set_status(self, message: str) -> None:
        """Update the status message for all status bar widgets."""
        [widget.update(message) for widget in self.query("#status_bar")]


if __name__ == "__main__":
    # Add path to the dynamic libraries
    # TODO Is this actually required, or are libraries already on the path?
    # sys.path.append(PATH_DYLIBS)

    # Initialize pygame for music playback.
    init_pygame()

    # Run the app.
    app = MusicPlayerApp()
    # app.cwd = "./demo_music"
    app.run()
