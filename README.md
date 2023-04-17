# textual-musicplayer

A simple music player (MP3, etc.) using Textual.

Version 0.0.0.0.0.0.1-prealpha

## Requirements

- textual - for TUI
- pygame - for music playing
- tinytag - for reading audio tags

## Sample audio

Sample music files used in the development of this app were downloaded from [SoundHelix](https://www.soundhelix.com/).  Copyright for these belongs to the appropriate artist.

- https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3
- https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3
- https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3

Pop these in `./demo_music` to get started.

## Basic installation (YMMV)

```bash
$ python3 -m venv ./venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ # textual console in another terminal, if you like
$ textual run --dev music_player.py
```

## Roadmap(?!)

- [x] play `mp3` music files
- [ ] see if I can work out how reactivity, events, widgets, etc. actually work
- [ ] make the bloody thing work!
- [ ] allow the user to select the music source directory (duh!)
- [ ] add support for `mp4`, `m4a`, `ogg` and/or `flac` files :-)
- [ ] clean up the UI (I'm looking at you, footer!)
- [ ] use `session.yaml` (or something similar maybe) to record session info (current track, position, volume, etc.)
- [ ] maybe - drag/drop source folder?
- [ ] maybe - "now playing" with chonky album artwork? (wouldn't that be neat?!)
- [ ] other cool stuff!
