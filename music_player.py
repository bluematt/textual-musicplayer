from __future__ import annotations

import sys
from os import walk, path
from typing import ClassVar

from textual.reactive import reactive
from tinytag import TinyTag
import pygame
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Container, Horizontal, Center, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Switch, Label, DataTable, Placeholder
from tinytag.tinytag import ID3, Ogg, Wave, Flac, Wma, MP4, Aiff

START_TRACK: int = 1

TRACK_EXT: tuple[str, ...] = ('.mp3',
                              # '.mp4', '.m4a', '.ogg', '.flac'
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
    def compose(self) -> ComposeResult:
        track_listing = DataTable(id="track_listing")
        track_listing.cursor_type = 'row'
        track_listing.zebra_stripes = True

        yield track_listing


class MusicPlayer(Static):
    """The music player user interface."""

    def compose(self) -> ComposeResult:
        yield TrackInformation()
        yield PlayerControls()
        yield TrackList()


class MusicPlayerApp(App):
    """A music player app."""

    CSS_PATH: ClassVar[CSSPathType | None] = "music_player.css"

    BINDINGS = [
        ("space", "toggle_play", "Play/Pause"),
        ("backspace", "stop_play", "Stop"),
        ("enter", "next_track", "Next track"),
        ("m", "toggle_mute", "Mute/Unmute"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("o", "open_directory", "Open directory"),
        ("r", "toggle_repeat", "Toggle repeat"),
        ("n", "toggle_random", "Toggle random"),
        ("q", "quit", "Quit"),
    ]

    # Whether the app is currently playing.
    playing: reactive[bool] = reactive(False)
    # Whether the app is muted.
    mute: reactive[bool] = reactive(False)

    # The current working directory (where music files are).
    cwd: reactive[str] = reactive('./demo_music')
    # The list of current tracks.
    tracks: reactive[list[tuple]] = reactive([])

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield MusicPlayer()
        yield Footer()

    def on_mount(self) -> None:
        # Scan for music in the current working directory.
        self.scan_track_directory()
        self.update_track_list()

        # Make sure we start the app stopped.
        # self.stop_track()
        self.set_focus(self.query_one('#track_listing'))

    def update_track_list(self) -> None:
        track_listing: DataTable = self.query_one(DataTable)
        tracks = iter(self.tracks)
        track_listing.add_columns(*next(tracks))
        track_listing.add_rows(tracks)

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_toggle_play(self) -> None:
        self.playing = not self.playing
        self.sub_title = "|>" if self.playing else "||"
        if self.playing:
            self.play_track(START_TRACK)

    def action_toggle_mute(self) -> None:
        self.mute = not self.mute

    def action_toggle_repeat(self) -> None:
        repeat_switch = self.query_one('#repeat_switch')
        repeat_switch.toggle()

    def action_toggle_random(self) -> None:
        random_switch = self.query_one('#random_switch')
        random_switch.toggle()

    def action_stop_play(self) -> None:
        self.stop_track()

    def action_open_directory(self) -> None:
        pass

    def action_scan_track_directory(self) -> None:
        self.scan_track_directory()

    def scan_track_directory(self) -> None:
        files: list[bytes | str] = [path.join(dir_path, f)
                                    for (dir_path, _dir_names, filenames) in walk(self.cwd)
                                    for f in filenames if
                                    f.endswith(TRACK_EXT) and not f.startswith(".")]
        tracks: list[TinyTag | ID3 | Ogg | Wave | Flac | Wma | MP4 | Aiff] = [TinyTag.get(f)
                                                                              for f in files]

        track_data: list[tuple[int | str, str, str, str, str, str, str]] = [
            ("Track", "Title", "Artist", "Album", "Length", "Genre", "File"), ]
        [track_data.append((idx + 1, t.title, t.artist, t.album, t.duration, t.genre, files[idx])) for idx, t in
         enumerate(tracks)]
        self.tracks = track_data

    def play_track(self, track_id: int) -> None:
        self.log(sys.path)
        self.log(self.tracks[track_id])
        self.stop_track()

        track = self.tracks[track_id]
        file = track[6]
        pygame.mixer.music.load(file)
        pygame.mixer.music.play()

        self.update_track_info(track)

    def update_track_info(self, track: tuple) -> None:
        pass

    def stop_track(self) -> None:
        pygame.mixer.init()

        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

        self.playing = False
        self.sub_title = "[]"


if __name__ == "__main__":
    # Add path to the dynamic libraries
    sys.path.append('./venv/lib/python3.7/site-packages/pygame/.dylibs')

    # Initialize pygame for music playback.
    pygame.init()
    pygame.mixer.init()

    app: MusicPlayerApp = MusicPlayerApp()
    app.run()
