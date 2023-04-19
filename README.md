# textual-musicplayer

A simple music player (MP3, etc.) using [Textual](https://textual.textualize.io/).

Version 0.0.0.0.0.0.1-prealpha

**This is very much a WIP. Use at your own risk.**

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
- [x] allow the user to select the music source directory (duh!)
- [ ] see if I can work out how reactivity, events, widgets, etc. actually work
- [ ] make the bloody thing work!
- [ ] add support for `mp4`, `m4a`, `ogg` and/or `flac` files :-)
- [ ] clean up the UI (I'm looking at you, footer!)
- [ ] use `session.yaml` (or something similar maybe) to record session info (current track, position, volume, etc.)
- [ ] maybe - drag/drop source folder?
- [ ] maybe - "now playing" with [chonky embedded album artwork](https://github.com/darrenburns/rich-pixels)? (wouldn't that be neat?!)
- [ ] other cool stuff!
