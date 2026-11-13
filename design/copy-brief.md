# Copy brief: Worship ChordPro

## The piece

The words on a small public website, and the opening of its GitHub README.
The site is a searchable library of Christian worship songs written in
ChordPro, the plain-text chord chart format that worship apps such as OnSong
and SongbookPro read. It lives at dsmithco.github.io/worship-chordpro and the
files live in the GitHub repo dsmithco/worship-chordpro. It is Dan Smith's
personal project, not Gray Sand Technology work, so do not mention Gray Sand.

## Who reads it

Worship leaders, church musicians and volunteers looking up a song to play
on Sunday, often on a phone at rehearsal. Some are church office staff who
print or project lyrics. They know songs and chords. Most do not know
copyright law.

## Facts you may use

- Songs are filed by the first letter of the title, one folder per song, and
  one file per version of it (a different tune, or a modern arrangement of an
  old hymn).
- Hymns in the public domain carry the whole chart, words and chords. In the
  United States a work published in 1930 or earlier is in the public domain
  in 2026. Other countries count differently, so a hymn free here may still
  be protected where the reader lives.
- The chords on the hymns were written for this project and are kept simple
  for guitar and keyboard. Any chart can be moved to another key on the page.
  The chord settings on public domain hymns are free to use.
- Most worship songs sung today were written after 1930 and are protected by
  copyright, for example 10,000 Reasons and Way Maker. The site lists them by
  title, writers, year and CCLI song number, and links to SongSelect, where a
  church that holds a license can get the official chart. The site shows no
  lyrics and no chords for these songs.
- The build that publishes the site checks every file. It refuses to publish
  lyrics or chords for a song marked as licensed, and it refuses a public
  domain claim dated after 1930.
- A CCLI Church Copyright License lets a church that holds one project,
  print and copy the lyrics of songs in the CCLI catalog for its own
  congregational worship. It does not let a website publish those songs for
  the public. Streaming a service online needs a separate license.
- This is not legal advice.
- Corrections and new songs come in as pull requests on GitHub
  (github.com/dsmithco/worship-chordpro).

## Dan's words, which the notice must carry

Dan asked that the site "explicitly say that this site does not give
copyright to its visitors and that appropriate license and permission is
always required before displaying printing or sharing lyrics from copy
protected work." Keep both points whole and plain: the site grants no rights
in anyone's songs to the people who visit it, and displaying, printing or
sharing the lyrics of a copyrighted song always needs the right license and
permission first. You may tidy his grammar ("copyright-protected"), not soften
the meaning.

## Format

Return each piece under its marker line, exactly as below, with nothing
before the first marker. Plain text, no markdown except where a piece says
otherwise. No dashes as punctuation.

[HOME_INTRO]
One or two sentences under the site name on the home page. Say what the
library is and what a visitor can do with it.

[HOME_NOTICE]
A short notice that sits above the song list on the home page. Two to four
short sentences. It carries both of Dan's points.

[FOOTER]
One or two sentences in the footer of every page. Carries Dan's two points in
the shortest form.

[LICENSED_PANEL]
Shown on the page of a copyrighted song, in place of a chart. Two or three
sentences: the chart is not on this site because the song is under
copyright, a church with a license can get it from SongSelect, and a license
and permission are needed before showing, printing or sharing its words.

[PD_LINE]
One sentence under a public domain hymn's chart: the words and music are in
the public domain in the United States and the chord setting is free to use.

[EMPTY]
One sentence for when a search finds nothing.

[COPYRIGHT_PAGE]
The Copyright page, in markdown: a few short sections with plain headings
(## level), 150 to 250 words in all. Cover what the site grants (nothing),
what needs a license, what is public domain and how the site decides, what a
CCLI license covers and does not, that it is not legal advice, and how to
report a problem or a song that should not be here.

[META_DESCRIPTION]
The page's meta description for search results, 50 to 160 characters.

[README_INTRO]
Two or three sentences that open the GitHub README: what the repo is and how
the songs are filed.
