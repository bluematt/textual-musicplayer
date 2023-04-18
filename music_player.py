from __future__ import annotations

import sys
from os import walk, path
from typing import ClassVar

from rich.console import RenderableType
from textual.binding import Binding
from tinytag import TinyTag
import pygame

from textual import log
from textual.reactive import reactive
from textual.app import App, ComposeResult, CSSPathType
from textual.containers import Horizontal, Center, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Switch, Label, DataTable, ContentSwitcher, Placeholder
from tinytag.tinytag import ID3, Ogg, Wave, Flac, Wma, MP4, Aiff

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


class TitleInfo(Static):
    """The track title."""
    title: reactive[str] = reactive("<untitled>")

    def render(self) -> RenderableType:
        return f"[bold]{self.title}[/]" if self.title else "[bold]<untitled>[/]"


class ArtistInfo(Static):
    """The track artist."""
    artist: reactive[str] = reactive("<unknown artist>")

    def render(self) -> RenderableType:
        return f"{self.artist}" if self.artist else "<unknown artist>"


class AlbumInfo(Static):
    """The track album."""
    album: reactive[str] = reactive("<unknown album>")

    def render(self) -> RenderableType:
        return f"[italic]{self.album}[/]" if self.album else "[italic]<unknown album>[/]"


class TrackInformation(Static):
    """The track information."""

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Now playing"),
            TitleInfo("[bold]<track>[/]", id="track_name"),
            ArtistInfo("<artist-name>", id="artist_name"),
            AlbumInfo("[italic]<album>[/]", id="album_name")
        )


class PlayerControls(Static):
    """The music controls."""

    def compose(self) -> ComposeResult:
        yield Center(Horizontal(
            Button("|>", id="play_button"),
            Button("||", id="pause_button"),
            Horizontal(
                Label("Repeat", classes="label"),
                Switch(value=False, id="repeat_switch", disabled=True),
                classes="container",
            ),
            Horizontal(
                Label("Random", classes="label"),
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


class DirectoryBrowser(Placeholder):
    """The directory browser."""
    BINDINGS = [
        Binding("o", "close_directory", "Close directory browser"),
    ]


class MusicPlayer(Static):
    """The main music player user interface."""

    def compose(self) -> ComposeResult:
        yield TrackInformation()
        yield PlayerControls()
        yield ContentSwitcher(
            TrackList(id="tracklist"),
            DirectoryBrowser(id="directory_browser"),
            id="context"
        )


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

    # The current working directory (where music files are).
    cwd: reactive[str] = reactive("./demo_music")

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

        # Show the tracklist
        self.query_one("#context", ContentSwitcher).current = "tracklist"

        # Focus the playlist
        self.focus_playlist()

        # Set the current track to be the first track in the playlist.
        # TODO Error handling for empty playlists.
        self.current_track = tuple(self.get_playlist().get_row_at(0))

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
        pygame.mixer.init()
        pygame.mixer.music.set_volume(1.0 - pygame.mixer.music.get_volume())

    def action_toggle_repeat(self) -> None:
        """Toggle repeating."""
        repeat_switch = self.query_one("#repeat_switch", Switch)
        repeat_switch.toggle()

    def action_toggle_random(self) -> None:
        """Toggle playlist randomisation."""
        random_switch = self.query_one("#random_switch", Switch)
        random_switch.toggle()

    def action_open_directory(self) -> None:
        self.query_one("#context", ContentSwitcher).current = "directory_browser"
        self.set_focus(self.query_one("#directory_browser", DirectoryBrowser))

    def action_close_directory(self) -> None:
        self.query_one("#context").current = "tracklist"

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
        [track_data.append((t.title, t.artist, t.album, self.format_duration(t.duration), t.genre, files[idx])) for
         idx, t in enumerate(tracks)]

        self.tracks = track_data

    def format_duration(self, duration: float) -> str:
        (m, s) = divmod(duration, 60.0)
        return f"{int(m)}\u2032{int(s):02}\u2033"

    def update_track_info(self, track: Track) -> None:
        """Update the UI with details of the current track."""
        self.query_one("#track_name").title = track[TRACK_TITLE_OFFSET]
        self.query_one("#artist_name").artist = track[TRACK_ARTIST_OFFSET]
        self.query_one("#album_name").album = track[TRACK_ALBUM_OFFSET]
        log(track)

    def is_playing(self) -> bool:
        """Return whether a track is currently playing."""
        pygame.mixer.init()
        return pygame.mixer.music.get_busy()

    def stop_music(self) -> None:
        """Stop playback."""
        pygame.mixer.init()
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "play_button":
            self.unpause()
        if event.button.id == "pause_button":
            self.pause()

        self.focus_playlist()

    def on_switch_changed(self, event: Switch.Changed) -> None:
        log(event.switch.id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handler for selecting a row in the data table."""
        self.current_track = tuple(event.data_table.get_row_at(event.cursor_row))

    def get_playlist(self) -> DataTable:
        """Return the playlist widget."""
        return self.query_one("#playlist", DataTable)

    def focus_playlist(self) -> None:
        self.set_focus(self.get_playlist())


if __name__ == "__main__":
    # Add path to the dynamic libraries
    sys.path.append(PATH_DYLIBS)

    # Initialize pygame for music playback.
    pygame.init()
    pygame.mixer.init()

    app: MusicPlayerApp = MusicPlayerApp()
    app.run()
