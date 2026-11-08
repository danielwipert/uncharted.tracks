"""Build the Top 50 site.

What this script does, step by step:
  1. Reads every song from songs.yaml.
  2. Checks each song has the fields the pages need.
  3. Fills in the HTML templates (in the templates/ folder) with that data.
  4. Writes the finished website into the _site/ folder.
  5. Copies the static files (CSS, fonts, images) next to it.

Run it from this folder with:
    python build.py
"""

import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "songs.yaml"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUTPUT = ROOT / "_site"

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
    if problems:
        raise SystemExit("songs.yaml needs fixing:\n  - " + "\n  - ".join(problems))


def add_extras(songs):
    """Add the things templates need that aren't typed in by hand."""
    for i, song in enumerate(songs):
        # Split the essay into paragraphs at each blank line.
        song["paragraphs"] = [p.strip() for p in song["essay"].split("\n\n") if p.strip()]
        # Previous = the song before it in the countdown (higher rank number).
        # Next = the song after it (lower rank number, closer to No. 1).
        song["prev"] = songs[i - 1] if i > 0 else None
        song["next"] = songs[i + 1] if i < len(songs) - 1 else None
        song["url"] = f"song/{song['rank']}/"


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

    # Home page.
    home = env.get_template("home.html").render(site=site, songs=songs, root="")
    (OUTPUT / "index.html").write_text(home, encoding="utf-8")

    # One page per song, at _site/song/<rank>/index.html
    song_template = env.get_template("song.html")
    for song in songs:
        page_dir = OUTPUT / "song" / str(song["rank"])
        page_dir.mkdir(parents=True)
        html = song_template.render(site=site, song=song, total=site["list_size"], root="../../")
        (page_dir / "index.html").write_text(html, encoding="utf-8")

    # CSS, images, etc.
    shutil.copytree(STATIC, OUTPUT / "static")

    # Tells GitHub Pages to serve the files as-is.
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Built {len(songs)} song pages + home page into {OUTPUT.name}/")


if __name__ == "__main__":
    build()
