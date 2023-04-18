from __future__ import annotations

import sys
from os import walk, path
from typing import ClassVar

from tinytag import TinyTag
import pygame

from textual import log
from textual.reactive import reactive
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Horizontal, Center, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Switch, Label, DataTable
from tinytag.tinytag import ID3, Ogg, Wave, Flac, Wma, MP4, Aiff

TrackType = TinyTag | ID3 | Ogg | Wave | Flac | Wma | MP4 | Aiff
Track = tuple[str, ...]

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


class TrackInformation(Static):
    """The track information."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Center(Label("Now playing")),
            Center(Label("[bold]<track>[/]", id="track_name")),
            Center(Label("<artist-name>", id="artist_name")),
            Center(Label("[italic]<album>[/]", id="album_name")),
            id="track_information"
        )


class PlayerControls(Static):
    """The music controls."""

    def compose(self) -> ComposeResult:
        yield Center(Horizontal(
            Button("|>", id="play_button"),
            Button("||", id="pause_button"),
            Horizontal(
                Label("Repeat", classes="label"),
                Switch(value=False, id="repeat_switch"),
                classes="container",
            ),
            Horizontal(
                Label("Random", classes="label"),
                Switch(value=False, id="random_switch"),
                classes="container",
            ),
        ))


class TrackList(VerticalScroll):
    """The scrollable list of tracks."""

    def compose(self) -> ComposeResult:
        playlist = DataTable(id="playlist")
        playlist.cursor_type = 'row'
        playlist.zebra_stripes = True

        yield playlist


class MusicPlayer(Static):
    """The main music player user interface."""

    def compose(self) -> ComposeResult:
        yield TrackInformation()
        yield PlayerControls()
        yield TrackList()


class MusicPlayerApp(App):
    """A music player app."""

    CSS_PATH: ClassVar[CSSPathType | None] = "music_player.css"

    BINDINGS = [
        ("space", "toggle_play", "Play/Pause"),
        ("m", "toggle_mute", "Mute/Unmute"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("o", "open_directory", "Open directory"),
        ("r", "toggle_repeat", "Toggle repeat"),
        ("n", "toggle_random", "Toggle random"),
        ("q", "quit", "Quit"),
    ]

    # Whether the app is muted.
    mute: reactive[bool] = reactive(False)

    # The current working directory (where music files are).
    cwd: reactive[str] = reactive('./demo_music')

    # The list of current tracks.
    tracks: reactive[list[tuple]] = reactive([])

    # The current track.
    current_track: reactive[Track | None] = reactive(None)

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
        if self.is_playing():
            self.play_current_track()

    def play_current_track(self) -> None:
        """Play the current track."""
        if self.is_playing():
            self.pause()
        else:
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

        # Focus the playlist and set the current track to be the first track in the playlist.
        # TODO Error handling for empty playlists.
        playlist: DataTable = self.get_playlist()
        self.set_focus(playlist)
        self.current_track = tuple(playlist.get_row_at(0))

    def update_playlist(self) -> None:
        """Update the playlist with the tracks from the current working directory."""
        playlist: DataTable = self.get_playlist()
        tracks = iter(self.tracks)
        playlist.add_columns(*next(tracks))
        playlist.add_rows(tracks)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_toggle_play(self) -> None:
        """Toggle play/pause."""
        pygame.mixer.init()
        if self.is_playing():
            self.pause()
        else:
            self.unpause()

    def pause(self):
        """Pause playback."""
        pygame.mixer.init()
        pygame.mixer.music.pause()

    def unpause(self) -> None:
        """Unpause playback."""
        pygame.mixer.init()
        pygame.mixer.music.unpause()

    def action_toggle_mute(self) -> None:
        """Toggle mute."""
        self.mute = not self.mute

    def action_toggle_repeat(self) -> None:
        """Toggle repeating."""
        repeat_switch = self.query_one('#repeat_switch')
        repeat_switch.toggle()

    def action_toggle_random(self) -> None:
        """Toggle playlist randomisation."""
        random_switch = self.query_one('#random_switch')
        random_switch.toggle()

    def action_open_directory(self) -> None:
        """Open a directory to get music."""
        pass

    def scan_track_directory(self) -> None:
        """Scan the current working directory for music files."""
        files: list[bytes | str] = [path.join(dir_path, f)
                                    for (dir_path, _dir_names, filenames) in walk(self.cwd)
                                    for f in filenames if
                                    f.endswith(TRACK_EXT) and not f.startswith(".")]

        # Get track metadata from music files.
        tracks: list[TrackType] = [TinyTag.get(f) for f in files]

        # Create a list of tuple(track info).
        track_data: list[Track] = [("Title", "Artist", "Album", "Length", "Genre", "File"), ]
        [track_data.append((t.title, t.artist, t.album, t.duration, t.genre, files[idx])) for idx, t in
         enumerate(tracks)]

        self.tracks = track_data

    def update_track_info(self, track: Track) -> None:
        """Update the UI with details of the current track."""
        log(track)

    def stop_music(self) -> None:
        """Stop playback."""
        pygame.mixer.init()
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

    def is_playing(self) -> bool:
        """Return whether a track is currently playing."""
        pygame.mixer.init()
        return pygame.mixer.music.get_busy()

    def play_track(self, track: Track):
        """Play a track."""
        if track:
            if self.is_playing():
                self.stop_music()

            file = track[TRACK_FILE_OFFSET]

            pygame.mixer.init()
            pygame.mixer.music.load(file)
            pygame.mixer.music.play()

            self.update_track_info(track)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler for selecting a row in the data table."""
        self.current_track = tuple(event.data_table.get_row_at(event.cursor_row))

    def get_playlist(self) -> DataTable:
        """Return the playlist widget."""
        return self.query_one("#playlist", DataTable)


if __name__ == "__main__":
    # Add path to the dynamic libraries
    sys.path.append('./venv/lib/python3.7/site-packages/pygame/.dylibs')

    # Initialize pygame for music playback.
    pygame.init()
    pygame.mixer.init()

    app: MusicPlayerApp = MusicPlayerApp()
    app.run()
