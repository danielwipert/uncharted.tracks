"""
Fill the master data set (data/master.csv) with details from Genius.

Step 2b of the track database. Runs in GitHub Actions ("Fill from Genius").
Adds genius_* columns plus apple_music_url / youtube_url / soundcloud_url.
Never touches the Spotify or MusicBrainz columns.

Needs a GitHub secret: GENIUS_ACCESS_TOKEN (genius.com/api-clients ->
Generate Access Token).

Lyrics are NOT collected (the API doesn't serve them, and they can't go on
the site). The song description and artist bio are kept as background for
Dan's own writing; they are other people's words and stay off the site.

Usage:
    python tools/fill_genius.py            only songs not checked yet
    python tools/fill_genius.py --refresh  re-check every song
"""

import argparse
import csv
import difflib
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
MASTER_CSV = REPO / "data" / "master.csv"
API = "https://api.genius.com"

GENIUS_COLUMNS = [
    "genius_match",          # found / not found
    "genius_url",
    "genius_title",          # the song title Genius matched, to spot wrong matches
    "genius_artist",
    "genius_songwriters",
    "genius_producers",
    "genius_label",          # from Genius's credits, when listed
    "genius_credits",        # other credits: "Mixing Engineer: Name; Mastering: Name"
    "genius_recorded_at",
    "genius_release_date",
    "apple_music_url",
    "youtube_url",
    "soundcloud_url",
    "genius_relationships",  # samples, covers, remixes
    "genius_description",    # background reading only, not for the site
    "genius_artist_bio",     # background reading only, not for the site
    "genius_instagram",
    "genius_twitter",
    "genius_song_id",
    "genius_checked_at",
]

LABEL_CREDITS = {"label", "labels", "record label"}


# ---------------------------------------------------------------------------
# Matching titles and names
# ---------------------------------------------------------------------------
def simplify(text):
    """Lowercase, strip accents, '(feat. ...)', '- Remastered' and punctuation."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = text.lower().replace("&", "and")
    text = re.sub(r"[\(\[](feat|ft|with|from)[^\)\]]*[\)\]]", "", text)
    text = re.sub(r"\s+-\s+.*$", "", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return " ".join(text.split())


def similar(a, b):
    a, b = simplify(a), simplify(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------------------
# Talking to Genius
# ---------------------------------------------------------------------------
class Genius:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "UnchartedTracks/1.0 (https://github.com/danielwipert/uncharted.tracks)",
        })
        self.cache = {}

    def get(self, path, **params):
        key = (path, tuple(sorted(params.items())))
        if key in self.cache:
            return self.cache[key]
        params["text_format"] = "plain"
        for attempt in range(5):
            time.sleep(0.4)  # be polite
            try:
                response = self.session.get(API + path, params=params, timeout=30)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 401:
                sys.exit("::error::Genius refused the access token. Check the GENIUS_ACCESS_TOKEN secret.")
            if response.status_code == 404:
                self.cache[key] = None
                return None
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** (attempt + 1))
                continue
            response.raise_for_status()
            self.cache[key] = response.json().get("response")
            return self.cache[key]
        print(f"  ::warning::Genius didn't answer for {path}; skipping.")
        return None

    def find_song(self, title, artist):
        """Search Genius and return the best matching search result, or None."""
        best, best_score = None, 0.0
        for query in (f"{simplify(title)} {simplify(artist)}", simplify(title)):
            found = self.get("/search", q=query) or {}
            for hit in found.get("hits") or []:
                song = hit.get("result") or {}
                artist_score = similar(song.get("primary_artist", {}).get("name"), artist)
                # Also accept the artist as one of a combined credit, e.g. "Ellur & Cai Alty".
                if artist_score < 0.85 and simplify(artist) in simplify(song.get("artist_names", "")):
                    artist_score = 0.9
                title_score = similar(song.get("title"), title)
                score = (artist_score + title_score) / 2
                if artist_score >= 0.85 and title_score >= 0.8 and score > best_score:
                    best, best_score = song, score
            if best:
                return best
        return None


def names(artists):
    return "; ".join(dict.fromkeys(a.get("name", "") for a in artists or [] if a.get("name")))


def trim(text, limit=1200):
    text = " ".join((text or "").split())
    if text in ("", "?"):
        return ""
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def song_details(genius, hit):
    song_id = hit["id"]
    data = genius.get(f"/songs/{song_id}") or {}
    song = data.get("song") or {}
    if not song:
        return None

    label, credits = [], []
    for perf in song.get("custom_performances") or []:
        role = (perf.get("label") or "").strip()
        who = names(perf.get("artists"))
        if not role or not who:
            continue
        if role.lower() in LABEL_CREDITS:
            label.append(who)
        else:
            credits.append(f"{role}: {who}")

    media = {m.get("provider"): m.get("url") for m in song.get("media") or [] if m.get("url")}

    relationships = []
    for rel in song.get("song_relationships") or []:
        related = [s.get("full_title") for s in rel.get("songs") or [] if s.get("full_title")]
        if related:
            kind = (rel.get("relationship_type") or rel.get("type") or "").replace("_", " ")
            relationships.append(f"{kind}: {', '.join(related[:3])}")

    out = {
        "genius_match": "found",
        "genius_song_id": song_id,
        "genius_url": song.get("url", ""),
        "genius_title": song.get("title") or hit.get("title", ""),
        "genius_artist": song.get("artist_names") or (hit.get("primary_artist") or {}).get("name", ""),
        "genius_songwriters": names(song.get("writer_artists")),
        "genius_producers": names(song.get("producer_artists")),
        "genius_label": "; ".join(label),
        "genius_credits": "; ".join(credits),
        "genius_recorded_at": song.get("recording_location") or "",
        "genius_release_date": song.get("release_date") or "",
        "apple_music_url": (f"https://music.apple.com/us/song/{song['apple_music_id']}"
                            if song.get("apple_music_id") else ""),
        "youtube_url": media.get("youtube", ""),
        "soundcloud_url": media.get("soundcloud", ""),
        "genius_relationships": "; ".join(relationships),
        "genius_description": trim((song.get("description") or {}).get("plain")),
    }

    artist_id = (song.get("primary_artist") or {}).get("id")
    if artist_id:
        artist = (genius.get(f"/artists/{artist_id}") or {}).get("artist") or {}
        out["genius_artist_bio"] = trim((artist.get("description") or {}).get("plain"))
        out["genius_instagram"] = (f"https://www.instagram.com/{artist['instagram_name']}"
                                   if artist.get("instagram_name") else "")
        out["genius_twitter"] = (f"https://x.com/{artist['twitter_name']}"
                                 if artist.get("twitter_name") else "")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def save(rows, columns):
    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Fill data/master.csv from Genius")
    parser.add_argument("--refresh", action="store_true", help="re-check songs already checked")
    args = parser.parse_args()

    token = os.environ.get("GENIUS_ACCESS_TOKEN")
    if not token:
        sys.exit("::error::No GENIUS_ACCESS_TOKEN found. Add it as a GitHub secret.")
    if not MASTER_CSV.exists():
        sys.exit("::error::data/master.csv not found. Run 'Pull from Spotify' first.")

    with MASTER_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = list(reader.fieldnames or [])
    columns += [c for c in GENIUS_COLUMNS if c not in columns]

    genius = Genius(token)
    todo = [r for r in rows if args.refresh or not r.get("genius_checked_at")]
    print(f"Checking {len(todo)} of {len(rows)} songs on Genius...\n")
    found = 0

    for i, row in enumerate(todo, 1):
        hit = genius.find_song(row["title"], row["artist"])
        details = song_details(genius, hit) if hit else None
        details = details or {"genius_match": "not found"}
        for c in GENIUS_COLUMNS:
            row[c] = details.get(c, "")
        row["genius_checked_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if details["genius_match"] == "found":
            found += 1
        writers = row["genius_songwriters"]
        print(f"  {i:>3}. {row['artist']} - {row['title']}: {row['genius_match']}"
              + (f" (writers: {writers})" if writers else ""))
        if i % 10 == 0:
            save(rows, columns)  # save as we go
    save(rows, columns)

    fields = ["genius_songwriters", "genius_producers", "genius_label", "genius_credits",
              "genius_recorded_at", "apple_music_url", "youtube_url", "genius_description"]
    lines = ["## Fill from Genius", "",
             f"Checked **{len(todo)}** songs: {found} found, {len(todo) - found} not found.", "",
             "| Field | Songs filled |", "|---|---|"]
    lines += [f"| {c.replace('genius_', '')} | {sum(1 for r in rows if r.get(c))} of {len(rows)} |"
              for c in fields]
    print("\n" + lines[2])
    summary("\n".join(lines))


if __name__ == "__main__":
    main()
