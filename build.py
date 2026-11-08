"""Build the Top 50 site.

What this script does, step by step:
  1. Reads every song from songs.yaml.
  2. Checks each song has the fields the pages need.
  3. Makes the faded-polaroid copies of each song photo (see photos.py).
  4. Fills in the HTML templates (in the templates/ folder) with that data.
  5. Writes the finished website into the _site/ folder.
  6. Copies the static files (CSS, images) next to it.

Run it from this folder with:
    python build.py
"""

import re
import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from photos import make_treated_photos

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "songs.yaml"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUTPUT = ROOT / "_site"
PHOTO_CACHE = ROOT / ".cache" / "photos"
WEAR_TEXTURE = STATIC / "img" / "wear.png"

# Every song must have these. Anything else (photo, songwriters...) is optional.
REQUIRED_FIELDS = [
    "rank", "slug", "title", "artist", "hometown", "record_label",
    "release_month", "headline", "standfirst", "essay",
]


def load_data():
    """Read songs.yaml and return the site settings and the songs (sorted 50 -> 1)."""
    with open(DATA_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    songs = sorted(data["songs"], key=lambda s: s["rank"], reverse=True)
    return data["site"], songs


def check_songs(songs):
    """Stop with a clear message if a song is missing something or two songs share a rank."""
    problems = []
    seen_ranks = set()
    for song in songs:
        name = song.get("title", "(untitled song)")
        for field in REQUIRED_FIELDS:
            if not song.get(field):
                problems.append(f"'{name}' is missing '{field}'")
        if song.get("rank") in seen_ranks:
            problems.append(f"Rank {song.get('rank')} is used more than once")
        seen_ranks.add(song.get("rank"))
        if song.get("photo") and not (STATIC / song["photo"]).exists():
            problems.append(f"'{name}' photo not found: static/{song['photo']}")
    if problems:
        raise SystemExit("songs.yaml needs fixing:\n  - " + "\n  - ".join(problems))


def spotify_embed(url):
    """Turn a normal Spotify song link into its player link."""
    m = re.search(r"open\.spotify\.com/(?:intl-[a-z]+/)?(track|album)/([A-Za-z0-9]+)", url or "")
    return f"https://open.spotify.com/embed/{m.group(1)}/{m.group(2)}" if m else ""


def apple_embed(url):
    """Turn a normal Apple Music link into its player link."""
    if url and "music.apple.com" in url:
        return url.replace("https://music.apple.com", "https://embed.music.apple.com")
    return ""


def youtube_embed(url):
    """Turn a normal YouTube link into its player link."""
    m = re.search(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})", url or "")
    return f"https://www.youtube-nocookie.com/embed/{m.group(1)}" if m else ""


def bandcamp_embed(track_id):
    """Bandcamp's player needs the track's number (from its Share/Embed code)."""
    if not track_id:
        return ""
    return (f"https://bandcamp.com/EmbeddedPlayer/track={track_id}/size=large/"
            "bgcol=f2ede3/linkcol=ff5a36/tracklist=false/artwork=small/transparent=true/")


def listen_rows(song):
    """The rows of the cassette insert, in order. Services without a link are skipped.
    'embed' = plays on the page when tapped; no embed = opens the service instead."""
    services = [
        ("Bandcamp", song.get("bandcamp_url"), bandcamp_embed(song.get("bandcamp_track_id")), 120, "buy it", True),
        ("Spotify", song.get("spotify_url"), spotify_embed(song.get("spotify_url")), 152, "", False),
        ("Apple Music", song.get("apple_music_url"), apple_embed(song.get("apple_music_url")), 175, "", False),
        ("YouTube", song.get("youtube_url"), youtube_embed(song.get("youtube_url")), 0, "video", False),
        ("YouTube Music", song.get("youtube_music_url"), "", 0, "opens app", False),
    ]
    rows = []
    for name, url, embed, height, note, highlight in services:
        if url:
            rows.append({"code": f"A{len(rows) + 1}", "name": name, "url": url, "embed": embed,
                         "height": height, "note": note, "highlight": highlight})
    return rows


def add_extras(songs):
    """Add the things templates need that aren't typed in by hand."""
    for i, song in enumerate(songs):
        # Split the essay into paragraphs at each blank line.
        song["paragraphs"] = [" ".join(p.split()) for p in song["essay"].split("\n\n") if p.strip()]
        # Previous = the song before it in the countdown (higher rank number).
        # Next = the song after it (lower rank number, closer to No. 1).
        song["prev"] = songs[i - 1] if i > 0 else None
        song["next"] = songs[i + 1] if i < len(songs) - 1 else None
        song["url"] = f"song/{song['rank']}/"
        # "Belfast, N. Ireland" -> "Belfast" (fits on the record sticker).
        song["hometown_short"] = song["hometown"].split(",")[0].strip()
        song["listen"] = listen_rows(song)
        # Each polaroid on the wall leans a little, in a repeating pattern.
        song["tilt"] = TILTS[i % len(TILTS)]


TILTS = ["-2.5deg", "2deg", "1.5deg", "-1.5deg", "-3deg", "2.5deg", "1deg", "-2deg"]


def group_for_home(songs):
    """Split the songs into groups of ten for the wall (No. 50-41, 40-31, ...)
    and the top 10, which gets its own bigger section."""
    parts = []
    for top in range(50, 10, -10):
        group = [s for s in songs if top - 9 <= s["rank"] <= top]
        if group:
            parts.append({"id": f"p{top}", "label": f"{top}–{top - 9}", "songs": group})
    top_ten = [s for s in songs if s["rank"] <= 10]
    return parts, top_ten


def make_photos(songs):
    """Bake the faded-polaroid copies of every song photo."""
    out_dir = OUTPUT / "static" / "img" / "treated"
    for song in songs:
        if not song.get("photo"):
            song["cover_img"] = song["square_img"] = None
            continue
        names = make_treated_photos(
            STATIC / song["photo"], out_dir, song["slug"], WEAR_TEXTURE, PHOTO_CACHE,
            focus_y=song.get("photo_focus_y", 0.25),
        )
        song["cover_img"] = f"static/img/treated/{names['cover']}"
        song["square_img"] = f"static/img/treated/{names['square']}"


def report_missing(songs):
    """Print (but don't stop for) things still to fill in."""
    for song in songs:
        todo = []
        if not song.get("photo"):
            todo.append("photo")
        if not song["listen"]:
            todo.append("listening links")
        elif song.get("bandcamp_url") and not song.get("bandcamp_track_id"):
            todo.append("bandcamp_track_id (so Bandcamp plays on the page)")
        if "[" in song["headline"] + song["essay"]:
            todo.append("writing")
        if todo:
            print(f"  No. {song['rank']} {song['title']}: still needs {', '.join(todo)}")


def build():
    site, songs = load_data()
    check_songs(songs)
    add_extras(songs)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"]),
    )

    # Start from an empty output folder each time.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir()

    # CSS, images, etc. (copied first so treated photos land beside them).
    shutil.copytree(STATIC, OUTPUT / "static")
    make_photos(songs)

    # Home page.
    parts, top_ten = group_for_home(songs)
    home = env.get_template("home.html").render(
        site=site, songs=songs, parts=parts, top_ten=top_ten, total=site["list_size"], root="")
    (OUTPUT / "index.html").write_text(home, encoding="utf-8")

    # One page per song, at _site/song/<rank>/index.html
    song_template = env.get_template("song.html")
    for song in songs:
        page_dir = OUTPUT / "song" / str(song["rank"])
        page_dir.mkdir(parents=True)
        html = song_template.render(site=site, song=song, total=site["list_size"], root="../../")
        (page_dir / "index.html").write_text(html, encoding="utf-8")

    # Tells GitHub Pages to serve the files as-is.
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")

    # While it's a hidden preview, ask search engines to stay away.
    robots = "User-agent: *\nDisallow: /\n" if site.get("hidden_preview") else "User-agent: *\nAllow: /\n"
    (OUTPUT / "robots.txt").write_text(robots, encoding="utf-8")

    print(f"Built {len(songs)} song pages + home page into {OUTPUT.name}/")
    report_missing(songs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build the Top 50 site.")
    parser.add_argument("--data", help="use a different songs file (for testing)")
    parser.add_argument("--out", help="write the site to a different folder (for testing)")
    args = parser.parse_args()
    if args.data:
        DATA_FILE = Path(args.data)
    if args.out:
        OUTPUT = Path(args.out)
    build()
