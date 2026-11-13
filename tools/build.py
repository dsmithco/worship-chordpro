#!/usr/bin/env python3
"""Check every song file and build the site into _site/.

  python3 tools/build.py            check, then build _site/
  python3 tools/build.py --check    check only, build nothing
  python3 -m http.server -d _site   look at it on localhost:8000

The check is the copyright guard, so it runs in CI before every deploy and a
failing song stops the whole publish. The rules:

  license public-domain  needs {year}, {lyricist} and {composer}, and every
                         year on the file (text, tune, translation) must be
                         at or before the US public domain line, which is
                         96 years before this year (1930 during 2026).
  license permission     needs {meta: permission ...} naming who granted it
                         and when. The chart may carry lyrics.
  license licensed       may carry facts only: no lyric line, no chord. The
                         site shows the facts and sends people to a licensed
                         source.

Song files live at songs/<LETTER>/<song-slug>/<variation>.cho, where LETTER
is the first letter of the title (0-9 for a title starting with a digit).
Every page is plain HTML written here, so a song reads without JavaScript;
site/assets/site.js only adds search, filters and transposing.
"""

import datetime
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
SONGS = ROOT / "songs"
SITE = ROOT / "site"
OUT = ROOT / "_site"
COPY = SITE / "copy.md"

BASE_URL = "https://dsmithco.github.io/worship-chordpro/"
REPO_URL = "https://github.com/dsmithco/worship-chordpro"
SITE_NAME = "Worship ChordPro"

TODAY = datetime.date.today()
PD_CUTOFF = TODAY.year - 96
LICENSES = {"public-domain", "licensed", "permission"}
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + ["0-9"]
YEAR_KEYS = ("year", "tune-year", "translation-year")
# Keys that may appear more than once in a file.
MULTI = {"composer", "lyricist", "artist", "translator"}
SINGLE = {"title", "subtitle", "key", "time", "tempo", "year", "copyright",
          "album", "capo", "duration", "sorttitle"}
BODY = {"c", "comment", "ci", "comment-italic", "start-of-verse", "sov",
        "start-of-chorus", "soc", "start-of-bridge", "sob", "eov", "eoc", "eob",
        "end-of-verse", "end-of-chorus", "end-of-bridge", "chorus"}

DIRECTIVE = re.compile(r"^\{\s*([a-z_-]+)\s*(?::\s*(.*?))?\s*\}$")
CHORD = re.compile(r"\[([^\]]+)\]")
YEAR = re.compile(r"^c?\.?\s*(\d{3,4})")


def esc(s):
    return html.escape(str(s), quote=True)


def letter_for(title):
    for ch in title:
        if ch.isalpha():
            return ch.upper()
        if ch.isdigit():
            return "0-9"
    return None


def parse(path):
    """Read a .cho file into (meta, lines). Lines are (kind, name_or_text, value)."""
    meta = {}
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        m = DIRECTIVE.match(line)
        if m:
            name, value = m.group(1).replace("_", "-"), m.group(2)
            if name == "meta" and value:
                key, _, rest = value.partition(" ")
                name, value = key.strip().lower(), rest.strip()
            if name in BODY or value is None:
                lines.append(("directive", name, value))
            elif name in MULTI:
                meta.setdefault(name, []).append(value)
            else:
                meta[name] = value
            continue
        if line.startswith("#"):
            continue
        lines.append(("lyric", raw.rstrip(), None))
    return meta, lines


def plain(text):
    return re.sub(r"\s+", " ", CHORD.sub("", text)).strip()


def check(path, meta, lines):
    errors = []
    rel = path.relative_to(ROOT)
    parts = path.relative_to(SONGS).parts
    if len(parts) != 3 or not path.name.endswith(".cho"):
        return [f"{rel}: song files go at songs/<LETTER>/<song-slug>/<variation>.cho"]
    letter, slug, _ = parts
    if letter not in LETTERS:
        errors.append(f"{rel}: '{letter}' is not a letter folder (A to Z, or 0-9)")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errors.append(f"{rel}: folder name '{slug}' must be lowercase words joined by hyphens")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.cho", path.name) or path.stem == "index":
        errors.append(f"{rel}: file name must be lowercase words joined by hyphens, and not 'index'")
    if not meta.get("title"):
        errors.append(f"{rel}: missing {{title: ...}}")

    lic = meta.get("license")
    if lic not in LICENSES:
        errors.append(f"{rel}: {{meta: license ...}} must be one of {', '.join(sorted(LICENSES))}")
        return errors

    lyric_lines = [text for kind, text, _ in lines if kind == "lyric" and text.strip()]
    if lic == "licensed":
        if lyric_lines or any(kind == "directive" and name == "chorus" for kind, name, _ in lines):
            errors.append(f"{rel}: a licensed song may not carry lyrics or chords on this site")
    elif lic == "permission":
        if not meta.get("permission"):
            errors.append(f"{rel}: license permission needs {{meta: permission <who granted it, and when>}}")
    elif lic == "public-domain":
        for key in ("year", "lyricist", "composer"):
            if not meta.get(key):
                errors.append(f"{rel}: public-domain needs {{{key}: ...}} so the claim can be checked")
        for key in YEAR_KEYS:
            value = meta.get(key)
            if not value:
                continue
            m = YEAR.match(value)
            if not m:
                errors.append(f"{rel}: {key} '{value}' must start with a year")
            elif int(m.group(1)) > PD_CUTOFF:
                errors.append(
                    f"{rel}: {key} {m.group(1)} is after {PD_CUTOFF}, so it is not public domain "
                    "in the US by date. Mark it licensed or record the permission."
                )

    if lyric_lines and CHORD.search("\n".join(lyric_lines)) and not meta.get("key"):
        errors.append(f"{rel}: a chart with chords needs {{key: ...}}")
    return errors


def year_of(value):
    m = YEAR.match(value or "")
    return int(m.group(1)) if m else 9999


def entry(path, meta, lines):
    lyric = [plain(text) for kind, text, _ in lines if kind == "lyric" and text.strip()]
    return {
        "id": path.stem,
        "file": path.name,
        "title": meta["title"],
        "subtitle": meta.get("subtitle", ""),
        "variation": meta.get("variation", ""),
        "license": meta["license"],
        "permission": meta.get("permission", ""),
        "hasChart": bool(lyric),
        "key": meta.get("key", ""),
        "time": meta.get("time", ""),
        "tune": meta.get("tune", ""),
        "meter": meta.get("meter", ""),
        "lyricist": meta.get("lyricist", []),
        "translator": meta.get("translator", []),
        "composer": meta.get("composer", []),
        "artist": meta.get("artist", []),
        "year": meta.get("year", ""),
        "tuneYear": meta.get("tune-year", ""),
        "translationYear": meta.get("translation-year", ""),
        "ccli": meta.get("ccli", ""),
        "arranger": meta.get("arranger", ""),
        "note": meta.get("note", ""),
        "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        "firstLine": lyric[0].rstrip(",;:") if lyric else "",
        "text": " ".join(lyric) if meta["license"] != "licensed" else "",
        "lines": lines,
    }


# Rendering a chart

def render_line(text):
    """One lyric line, chords stacked over the syllable they were typed before."""
    if not CHORD.search(text):
        return f'<div class="ln">{esc(text.strip()) or "&nbsp;"}</div>'
    segs, pos, chord = [], 0, None
    for m in CHORD.finditer(text):
        segs.append((chord, text[pos:m.start()]))
        chord, pos = m.group(1), m.end()
    segs.append((chord, text[pos:]))

    words = [[]]
    for chord, t in segs:
        for i, chunk in enumerate(t.split(" ")):
            if i:
                words.append([])
            c = chord if i == 0 else None
            if c is None and chunk == "":
                continue
            words[-1].append((c, chunk))

    out = []
    for word in words:
        if not word:
            continue
        pieces = []
        for c, t in word:
            ch = f'<span class="c" data-c="{esc(c)}">{esc(c)}</span>' if c else '<span class="c"></span>'
            pieces.append(f'<span class="p">{ch}<span class="t">{esc(t) or "&nbsp;"}</span></span>')
        out.append(f'<span class="w">{"".join(pieces)}</span>')
    return f'<div class="ln has-c">{" ".join(out)}</div>'


def render_chart(lines):
    blocks = []
    current = None
    last_chorus = "Chorus"

    def close():
        nonlocal current
        if current and current["lines"]:
            blocks.append(current)
        current = None

    for kind, a, b in lines:
        if kind == "lyric":
            if current is None:
                current = {"kind": "verse", "label": "", "lines": []}
            if a.strip():
                current["lines"].append(render_line(a))
            elif current["lines"]:
                close()
            continue
        name, value = a, b
        if name in ("start-of-verse", "sov", "start-of-chorus", "soc", "start-of-bridge", "sob"):
            close()
            kind_ = {"verse": "verse", "sov": "verse", "chorus": "chorus", "soc": "chorus",
                     "bridge": "bridge", "sob": "bridge"}[name.replace("start-of-", "")]
            label = value or ""
            if kind_ == "chorus":
                last_chorus = label or "Chorus"
            current = {"kind": kind_, "label": label, "lines": []}
        elif name.startswith("end-of") or name in ("eov", "eoc", "eob"):
            close()
        elif name == "chorus":
            close()
            blocks.append({"kind": "recall", "label": value or last_chorus, "lines": []})
        elif name in ("c", "comment", "ci", "comment-italic") and value:
            close()
            blocks.append({"kind": "cue", "label": value, "lines": []})
    close()

    out = []
    for blk in blocks:
        if blk["kind"] == "recall":
            out.append(f'<p class="sec-label recall">{esc(blk["label"])}</p>')
        elif blk["kind"] == "cue":
            out.append(f'<p class="cue">{esc(blk["label"])}</p>')
        else:
            head = f'<h3 class="sec-label">{esc(blk["label"])}</h3>' if blk["label"] else ""
            out.append(f'<section class="sec {blk["kind"]}">{head}{"".join(blk["lines"])}</section>')
    return "\n".join(out)


# Copy, placed as Gemini wrote it

def load_copy():
    pieces, name = {}, None
    for line in COPY.read_text(encoding="utf-8").splitlines():
        m = re.fullmatch(r"\[([A-Z_]+)\]", line.strip())
        if m:
            name = m.group(1)
            pieces[name] = []
        elif name:
            pieces[name].append(line)
    return {k: "\n".join(v).strip() for k, v in pieces.items()}


def linkify(text):
    out = esc(text)
    return re.sub(r"(?<![/\w])(github\.com/dsmithco/worship-chordpro)\b",
                  r'<a href="https://\1">\1</a>', out)


def md(text):
    """The small slice of markdown the copy uses: ## headings and paragraphs."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if block.startswith("## "):
            out.append(f"<h2>{esc(block[3:].strip())}</h2>")
        else:
            out.append(f"<p>{linkify(' '.join(block.split()))}</p>")
    return "\n".join(out)


# Pages

PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def key_hue(label):
    """The Worship Sets key colour: twelve roots 30 degrees apart (lib/keyHue.ts)."""
    m = re.match(r"^([A-G])([#b]?)", (label or "").strip())
    if not m:
        return None
    pc = (PITCH[m.group(1)] + (1 if m.group(2) == "#" else 11 if m.group(2) == "b" else 0)) % 12
    return (pc * 30 + 200) % 360


def key_tile(label, cls="key"):
    h = key_hue(label)
    if h is None:
        return f'<span class="{cls} none" aria-label="Copyrighted">&copy;</span>'
    return f'<span class="{cls}" style="--kh:{h}">{esc(label)}</span>'


ICON_SEARCH = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M20 20l-4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
ICON_BACK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'


def page(*, title, description, path, root, main, copy, body_class="", jsonld=None, after=""):
    url = BASE_URL + path
    full_title = title if title == SITE_NAME else f"{title} | {SITE_NAME}"
    ld = ""
    if jsonld:
        ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{BASE_URL}assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME}: worship songs in ChordPro">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#eef0f3" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1012" media="(prefers-color-scheme: dark)">
<link rel="icon" href="{root}assets/icon.svg" type="image/svg+xml">
<link rel="preload" href="{root}assets/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/fonts/fonts.css">
<link rel="stylesheet" href="{root}assets/site.css">
<script>document.documentElement.classList.add("js")</script>
{ld}
</head>
<body class="{body_class}">
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="wrap top-in">
    <a class="mark" href="{root}">{SITE_NAME}</a>
    <nav class="top-nav" aria-label="Site">
      <a href="{root}copyright.html"{' aria-current="page"' if body_class == "legal" else ""}>Copyright</a>
      <a href="{REPO_URL}">GitHub</a>
    </nav>
  </div>
</header>
<main id="main">
{main}
</main>
<footer class="foot">
  <div class="wrap"><p>{esc(copy["FOOTER"])} <a href="{root}copyright.html">Copyright</a></p></div>
</footer>
{after}
<script src="{root}assets/site.js" defer></script>
</body>
</html>
"""


def names(items):
    items = [i for i in items if i]
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def credits(v):
    """The by-line under a title: writers for a modern song, words and music for a hymn."""
    if v["license"] == "licensed" or not v["lyricist"]:
        return f'<p class="sheet-by">{esc(names(v["composer"]))}</p>'
    words = names(v["lyricist"])
    if v["translator"]:
        words += f", tr. {names(v['translator'])}"
    music = names(v["composer"] + ([v["arranger"]] if v["arranger"] else []))
    if set(v["composer"]) == set(v["lyricist"]):
        return f'<p class="sheet-by">{esc(words)}</p>'
    return (f'<p class="sheet-by"><span><small>Words</small> {esc(words)}</span>'
            f'<span><small>Music</small> {esc(music)}</span></p>')


def short_label(v, song_title):
    """What a version is called on its chip: the tune for a hymn, else what sets it apart."""
    if v["hasChart"] and v["tune"]:
        return re.sub(r"\s*\(.*\)", "", v["tune"]).title().replace("'S", "'s")
    if v["title"] != song_title:
        m = re.search(r"\(([^)]+)\)", v["title"])
        if m and v["title"].startswith(song_title):
            return m.group(1)
        return v["title"]
    return v["artist"][0] if v["artist"] else v["title"]


def songselect(v):
    if v["ccli"]:
        return f"https://songselect.ccli.com/songs/{v['ccli']}"
    return f"https://songselect.ccli.com/search/results?search={quote_plus(v['title'])}"


def song_page(song, v, copy):
    letter, slug = song["letter"], song["slug"]
    lead = song["variations"][0]
    is_lead = v is lead
    path = f"songs/{letter}/{slug}/" + ("" if is_lead else f"{v['id']}.html")
    root = "../../../"

    facts = []
    if v["key"]:
        facts.append(f'<span class="fact fact-key" data-key-out>{esc(v["key"])}</span>')
    if v["time"]:
        facts.append(f'<span class="fact">{esc(v["time"])}</span>')
    if v["year"]:
        facts.append(f'<span class="fact">{esc(year_of(v["year"]))}</span>')
    if v["ccli"]:
        facts.append(f'<span class="fact"><small>CCLI</small> {esc(v["ccli"])}</span>')

    versions = ""
    if len(song["variations"]) > 1:
        chips = []
        for other in song["variations"]:
            href = "./" if other is lead else f"{other['id']}.html"
            cur = ' aria-current="page"' if other is v else ""
            chips.append(f'<a class="chip" href="{href}"{cur}>{esc(short_label(other, song["title"]))}</a>')
        versions = f'<nav class="chips versions" aria-label="Versions">{"".join(chips)}</nav>'

    head = f"""<header class="sheet-head">
  <div class="sheet-id"><h1 class="sheet-title">{esc(v["title"])}</h1>{credits(v)}</div>
  <div class="sheet-facts">{"".join(facts)}</div>
</header>"""

    dock = ""
    if v["hasChart"]:
        license_line = copy["PD_LINE"] if v["license"] == "public-domain" else f"Shown with permission: {v['permission']}."
        body = f"""<div class="sheet-body chart" data-key="{esc(v["key"])}">
{render_chart(v["lines"])}
</div>
<footer class="sheet-foot"><span>{esc(license_line)}</span><a href="{esc(v["file"])}" download>Download .cho</a></footer>"""
        dock = f"""<div class="dock" data-tools hidden>
  <div class="dock-in">
    <button type="button" class="rb" data-tr="-1" aria-label="Key down">&minus;</button>
    <button type="button" class="rb key-now" data-tr="0" aria-label="Back to the original key"><output data-key-out>{esc(v["key"])}</output></button>
    <button type="button" class="rb" data-tr="1" aria-label="Key up">+</button>
    <span class="dock-sep" aria-hidden="true"></span>
    <button type="button" class="rb wide" data-toggle-chords aria-pressed="true">Chords</button>
    <button type="button" class="rb" data-size aria-label="Text size">Aa</button>
    <button type="button" class="rb" data-print aria-label="Print"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg></button>
  </div>
</div>"""
    else:
        body = f"""<div class="licensed">
  <a class="btn" href="{esc(songselect(v))}" rel="noopener">Open in SongSelect</a>
  <p>{esc(copy["LICENSED_PANEL"])}</p>
</div>"""

    main = f"""<div class="wrap sheet-wrap">
<a class="back" href="{root}">{ICON_BACK}Songs</a>
{versions}
<article class="sheet">
{head}
{body}
</article>
</div>"""

    if v["hasChart"]:
        desc = f"{v['title']}: words and chords in {v['key']}. {v['firstLine']}."
        if len(desc) > 158:
            desc = f"{v['title']}: words and chords in {v['key']}, as a ChordPro chart."
    else:
        desc = f"{v['title']} by {names(v['composer']) or 'its writers'}: CCLI number and a SongSelect link."
    ld = {
        "@context": "https://schema.org",
        "@type": "MusicComposition",
        "name": v["title"],
        "url": BASE_URL + path,
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": BASE_URL},
    }
    if v["lyricist"]:
        ld["lyricist"] = [{"@type": "Person", "name": n} for n in v["lyricist"]]
    if v["composer"]:
        ld["composer"] = [{"@type": "Person", "name": n} for n in v["composer"]]
    if v["year"]:
        ld["datePublished"] = str(year_of(v["year"]))
    if v["key"]:
        ld["musicalKey"] = v["key"]
    if v["license"] == "public-domain":
        ld["license"] = "https://creativecommons.org/publicdomain/mark/1.0/"
    title = v["title"] if is_lead else f"{v['title']} ({short_label(v, song['title'])})"
    return path, page(title=title, description=desc, path=path, root=root, main=main,
                      copy=copy, body_class="song-page", jsonld=ld, after=dock)


def home_page(catalog, copy):
    by_letter = {}
    for s in catalog:
        by_letter.setdefault(s["letter"], []).append(s)

    groups = []
    for letter in LETTERS:
        rows = []
        for s in by_letter.get(letter, []):
            lead = s["variations"][0]
            charts = [v for v in s["variations"] if v["hasChart"]]
            kinds = (["chart"] if charts else []) + (["link"] if len(charts) < len(s["variations"]) else [])
            sub = lead["firstLine"] or names(lead["composer"])
            others = sorted({v["title"] for v in s["variations"] if v["title"] != s["title"]})
            trail = f'<span class="row-trail">{len(s["variations"])} versions</span>' if len(s["variations"]) > 1 else ""
            q = " ".join([s["title"], sub, " ".join(others)] + [
                " ".join([v["title"], v["variation"], v["tune"], " ".join(v["lyricist"] + v["composer"]
                         + v["translator"] + v["artist"]), " ".join(v["tags"]), v["ccli"]])
                for v in s["variations"]
            ])
            q = " ".join(re.sub(r"[^a-z0-9 ]+", " ", q.lower()).split())
            key = charts[0]["key"] if charts else ""
            rows.append(f"""<li data-kind="{" ".join(kinds)}" data-key="{esc(key)}" data-id="{esc(s["id"])}" data-q="{esc(q)}">
<a class="row" href="songs/{s["letter"]}/{s["slug"]}/">{key_tile(key)}<span class="row-main"><span class="row-title">{esc(s["title"])}</span><span class="row-sub">{esc(sub)}</span></span>{trail}</a>
</li>""")
        if rows:
            groups.append(f"""<section class="group" id="letter-{letter}" data-letter="{letter}">
<h2 class="group-h">{letter}</h2>
<ul class="list">
{"".join(rows)}
</ul>
</section>""")

    rail = "".join(f'<a href="#letter-{l}" data-thumb="{l}">{"#" if l == "0-9" else l}</a>'
                   for l in LETTERS if l in by_letter)
    keys = sorted({v["key"] for s in catalog for v in s["variations"] if v["hasChart"] and v["key"]},
                  key=lambda k: (key_hue(k) - 200) % 360)
    key_chips = "".join(
        f'<button type="button" class="chip key-chip" data-key-chip="{esc(k)}" aria-pressed="false" style="--kh:{key_hue(k)}">{esc(k)}</button>'
        for k in keys)

    main = f"""<div class="wrap home-wrap">
<h1 class="page-title">Songs</h1>
<div class="finder" data-finder>
  <label class="search">{ICON_SEARCH}<span class="vh">Search songs</span>
    <input type="search" class="field" placeholder="Search" autocomplete="off" spellcheck="false" data-q>
  </label>
  <div class="chips" role="group" aria-label="Filter">
    <button type="button" class="chip" data-kind-chip="" aria-pressed="true">All</button>
    <button type="button" class="chip" data-kind-chip="chart" aria-pressed="false">Charts</button>
    <button type="button" class="chip" data-kind-chip="link" aria-pressed="false">SongSelect</button>
    <span class="chip-gap" aria-hidden="true"></span>
    {key_chips}
  </div>
</div>
<p class="empty" data-empty hidden>{esc(copy["EMPTY"])}</p>
{"".join(groups)}
<nav class="az" aria-label="Jump to letter" data-az>{rail}</nav>
</div>"""
    ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": BASE_URL,
        "description": copy["META_DESCRIPTION"],
        "potentialAction": {
            "@type": "SearchAction",
            "target": BASE_URL + "?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }
    return page(title=SITE_NAME, description=copy["META_DESCRIPTION"], path="", root="",
                main=main, copy=copy, body_class="home", jsonld=ld)


def copyright_page(copy):
    main = f"""<div class="wrap legal-wrap">
<a class="back" href="./">{ICON_BACK}Songs</a>
<article class="sheet legal">
<h1 class="sheet-title">Copyright</h1>
{md(copy["COPYRIGHT_PAGE"])}
</article>
</div>"""
    return page(title="Copyright", description="What this site grants, what needs a license, and how public domain is decided.",
                path="copyright.html", root="", main=main, copy=copy, body_class="legal")


def not_found(copy):
    main = f"""<div class="wrap legal-wrap">
<a class="back" href="/worship-chordpro/">{ICON_BACK}Songs</a>
<article class="sheet legal"><h1 class="sheet-title">Page not found</h1></article>
</div>"""
    return page(title="Page not found", description="That address does not match a song.",
                path="404.html", root="/worship-chordpro/", main=main, copy=copy, body_class="legal")


def llms(catalog):
    lines = [f"# {SITE_NAME}", "",
             "> Christian worship songs in ChordPro. Public domain hymns carry full charts; "
             "copyrighted songs carry facts and a SongSelect link only. This site grants no rights "
             "in any song; displaying, printing or sharing copyrighted lyrics needs a license and permission.",
             "", f"- [Copyright notice]({BASE_URL}copyright.html)", f"- [Song files]({REPO_URL})", "", "## Songs", ""]
    for s in catalog:
        lead = s["variations"][0]
        kind = "chart" if lead["hasChart"] else "link only"
        lines.append(f"- [{s['title']}]({BASE_URL}songs/{s['letter']}/{s['slug']}/): {kind}")
    return "\n".join(lines) + "\n"


def main():
    check_only = "--check" in sys.argv
    errors = []
    songs = {}
    for path in sorted(SONGS.rglob("*")):
        if path.is_dir() or path.name.startswith("."):
            continue
        if path.suffix != ".cho":
            errors.append(f"{path.relative_to(ROOT)}: only .cho files belong under songs/")
            continue
        meta, lines = parse(path)
        problems = check(path, meta, lines)
        if problems:
            errors.extend(problems)
            continue
        letter, slug = path.relative_to(SONGS).parts[:2]
        songs.setdefault((letter, slug), []).append(entry(path, meta, lines))

    # A variation may carry its own title (Cornerstone sits with My Hope Is
    # Built), but the song's folder is filed under the letter of one of them.
    for (letter, slug), variations in sorted(songs.items()):
        if not any(letter_for(v["title"]) == letter for v in variations):
            titles = ", ".join(sorted({v["title"] for v in variations}))
            errors.append(f"songs/{letter}/{slug}: no title here starts with {letter} ({titles})")
    if errors:
        print(f"{len(errors)} problem(s):", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)

    catalog = []
    for (letter, slug), variations in sorted(songs.items()):
        # A chart we can show leads, then the oldest, then a title on the folder's letter.
        variations.sort(key=lambda v: (not v["hasChart"], letter_for(v["title"]) != letter,
                                       year_of(v["year"]), v["title"]))
        catalog.append({
            "id": f"{letter}/{slug}",
            "letter": letter,
            "slug": slug,
            "title": variations[0]["title"],
            "variations": variations,
        })
    catalog.sort(key=lambda s: re.sub(r"[^a-z0-9 ]", "", s["title"].lower()))

    charts = sum(1 for s in catalog for v in s["variations"] if v["hasChart"])
    total = sum(len(s["variations"]) for s in catalog)
    print(f"ok: {len(catalog)} songs, {total} files, {charts} with a chart, public domain line {PD_CUTOFF}")
    if check_only:
        return

    copy = load_copy()
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE / "assets", OUT / "assets")
    shutil.copytree(SONGS, OUT / "songs", ignore=shutil.ignore_patterns(".*"))

    urls = [BASE_URL, BASE_URL + "copyright.html"]
    for s in catalog:
        for v in s["variations"]:
            path, doc = song_page(s, v, copy)
            target = OUT / (path + "index.html" if path.endswith("/") else path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(doc, encoding="utf-8")
            urls.append(BASE_URL + path)

    (OUT / "index.html").write_text(home_page(catalog, copy), encoding="utf-8")
    (OUT / "copyright.html").write_text(copyright_page(copy), encoding="utf-8")
    (OUT / "404.html").write_text(not_found(copy), encoding="utf-8")
    (OUT / "llms.txt").write_text(llms(catalog), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{esc(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    # Lyrics for full-text search, only where the site may show them.
    search = {s["id"]: " ".join(v["text"] for v in s["variations"] if v["text"]) for s in catalog}
    (OUT / "search.json").write_text(json.dumps({k: v for k, v in search.items() if v},
                                                ensure_ascii=False, separators=(",", ":")))
    (OUT / ".nojekyll").write_text("")
    print(f"built {OUT.relative_to(ROOT)}/ ({len(urls)} pages)")


if __name__ == "__main__":
    main()
