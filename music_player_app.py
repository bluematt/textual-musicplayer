from __future__ import annotations

from collections import deque
from os import path
from random import shuffle
from typing import Optional

from rich_pixels import Pixels
from textual import on
from textual.app import App
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.reactive import Reactive
from textual.timer import Timer
from textual.widgets import Button
from textual.widgets._data_table import RowKey  # noqa - required to extend DataTable
from textual.widgets._directory_tree import DirEntry  # noqa - required to extend DirectoryTree
from tinytag import TinyTag

from browser_screen import BrowserScreen
from const import TrackPath, FRAME_RATE
from help_screen import HelpScreen
from helpers import get_files_in_directory, get_playback_position, unpause_playback, play_track, pause_playback, \
    stop_playback, format_duration
from now_playing_screen import NowPlayingScreen
from track import Track
from track_list import TrackList
from track_screen import TrackScreen


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
