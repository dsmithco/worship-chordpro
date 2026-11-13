# Worship ChordPro

Worship ChordPro is a searchable library of worship song chord charts by Dan Smith. Public domain hymns include words and chords, while copyrighted songs list details and link to SongSelect.

Site: https://dsmithco.github.io/worship-chordpro/

## Copyright

This site does not give copyright to its visitors. Appropriate license and permission is always required before displaying, printing, or sharing lyrics from copy protected work.

The full notice is on the site at [copyright.html](https://dsmithco.github.io/worship-chordpro/copyright.html).

## Layout

```
songs/<LETTER>/<song-slug>/<version>.cho
songs/A/amazing-grace/new-britain.cho      public domain hymn, full chart
songs/A/amazing-grace/chris-tomlin.cho     copyrighted version, facts only
```

`0-9` holds titles that start with a number.

## Add a song

Every file needs `{title}` and `{meta: license ...}`, one of:

- `public-domain`: needs `{lyricist}`, `{composer}`, `{year}` and `{key}`. Every year on the file must be 1930 or earlier (the US line moves forward each January).
- `licensed`: facts only (`{composer}` for each writer, `{year}`, `{artist}`, `{meta: ccli ...}`). No lyric or chord lines.
- `permission`: a chart shown with the owner's permission. Needs `{meta: permission <who granted it, and when>}`.

Run the check, then open a pull request:

```
python3 tools/build.py --check
python3 tools/build.py && python3 -m http.server -d _site
```

The same check runs on every push and blocks the deploy if a file breaks a rule.

## License

Site code: MIT (LICENSE). Chord settings on the public domain hymns: free to use, no rights reserved. Fonts: Inter, SIL Open Font License.
