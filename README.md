# textual-musicplayer AKA `tTunes`

A simple music player (MP3, etc.) using [Textual](https://textual.textualize.io/).

![screenshot.png](screenshot.png)

Version 0.0.0.0.0.0.3-prealpha (not even joking—this is a learning experience for me, so the code will *very*
unoptimised).

**This is very much a WIP. Use at your own risk.**

## Requirements

- textual - for TUI
- pygame - for music playing
- tinytag - for reading audio tags

## Sample audio

[Sample music files](https://www.soundhelix.com/audio-examples) used in the development of this app were downloaded
from [SoundHelix](https://www.soundhelix.com/). Copyright for these belongs to the appropriate artist(s).

If you don't have any music to hand, pop these in `./demo_music` to get started.

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
- [x] add support for `ogg` 
- [x] make the bloody thing work!
- [x] make the bloody thing work better!
- [ ] make the bloody thing work even better!
- [ ] add support for `mp4`, `m4a`, `ogg` and/or `flac` files :-)
- [ ] clean up the UI (I'm looking at you, footer!)
- [ ] record session info (current track, position, volume, etc.) so that playback starts where you left off last time
- [ ] maybe - drag/drop source folder?
- [ ] maybe - "now playing" with [chonky embedded album artwork](https://github.com/darrenburns/rich-pixels)? (wouldn't
  that be neat?!)
- [ ] other cool stuff!?!

## Notes

- If you are running this with the `textual console`, it can get a little chuggy. It seems pretty swift when running
  stand-alone.
