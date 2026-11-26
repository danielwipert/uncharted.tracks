"""
Pull songs from your Spotify playlists into the master data set (data/master.csv).

This is step 1 of the track database. Later steps (MusicBrainz, monthly
listeners) add more columns to the same file. This script never deletes
those extra columns: it only updates the Spotify columns.

Setup (one time): see docs/track-database.md, "Step 1: Spotify app".

Use it (from the repo folder, in PowerShell):
    python tools/pull_spotify.py --list
        Shows all your playlists with their IDs.
    python tools/pull_spotify.py --playlist "Top 50 candidates"
        Pulls one playlist (by name or ID). Repeat --playlist for more.

The first run opens your browser to log in to Spotify. After that, the
login is saved in .spotify_token.json (kept out of git) and reused.
"""

import argparse
import base64
import csv
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
MASTER_CSV = REPO / "data" / "master.csv"
TOKEN_FILE = REPO / ".spotify_token.json"
ENV_FILE = REPO / ".env"

REDIRECT_URI = "http://127.0.0.1:8888/callback"  # must match your Spotify app exactly
SCOPES = "playlist-read-private playlist-read-collaborative"
API = "https://api.spotify.com/v1"

# The Spotify columns, in order. Other columns already in master.csv
# (from later steps) are kept and placed after these.
SPOTIFY_COLUMNS = [
    "spotify_track_id",   # the key that links every sheet together
    "title",
    "artist",             # main (first) artist
    "featured_artists",   # anyone else credited, separated by "; "
    "spotify_artist_id",
    "spotify_artist_url",
    "genres",             # from Spotify; often empty for small artists
    "album",
    "album_type",         # single / album / compilation
    "album_track_count",  # helps tell an EP (2-6 tracks) from an album
    "track_number",
    "release_date",
    "release_month",      # e.g. "January", for the song page
    "duration",           # m:ss, for the song page
    "duration_ms",
    "explicit",
    "isrc",               # universal song ID, used to find it on MusicBrainz
    "upc",                # album barcode
    "spotify_url",
    "cover_url",          # biggest album image
    "playlists",          # which of your playlists it's on, "; " separated
    "first_added_at",     # earliest date you added it to any of them
    "spotify_pulled_at",
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def load_env():
    """Read KEY=value lines from .env into the environment (if the file exists)."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


def ms_to_mss(ms):
    seconds = round(int(ms) / 1000)
    return f"{seconds // 60}:{seconds % 60:02d}"


def release_month(date_text):
    """'2026-01-17' -> 'January'. Year-only dates give ''."""
    parts = (date_text or "").split("-")
    if len(parts) >= 2:
        return datetime(2000, int(parts[1]), 1).strftime("%B")
    return ""


def split_list(text):
    return [p.strip() for p in (text or "").split(";") if p.strip()]


# ---------------------------------------------------------------------------
# Logging in to Spotify (Authorization Code with PKCE: no secret needed)
# ---------------------------------------------------------------------------
def save_token(token):
    token["expires_at"] = time.time() + token.get("expires_in", 3600) - 60
    TOKEN_FILE.write_text(json.dumps(token, indent=2), encoding="utf-8")
    return token


def browser_login(client_id):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")
    state = secrets.token_urlsafe(16)

    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Spotify login done. You can close this tab.</h2>")

        def log_message(self, *args):
            pass  # keep the terminal quiet

    server = http.server.HTTPServer(("127.0.0.1", 8888), Handler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    })
    print("Opening your browser to log in to Spotify...")
    print("If it doesn't open, copy this link into your browser:\n" + url)
    webbrowser.open(url)
    thread.join(timeout=300)
    server.server_close()

    if result.get("state") != state or "code" not in result:
        sys.exit(f"Login didn't finish: {result.get('error', 'no reply from Spotify')}")

    response = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": verifier,
    }, timeout=30)
    response.raise_for_status()
    return save_token(response.json())


def get_token(client_id):
    if TOKEN_FILE.exists():
        token = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        if time.time() < token.get("expires_at", 0):
            return token
        if token.get("refresh_token"):
            response = requests.post("https://accounts.spotify.com/api/token", data={
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
                "client_id": client_id,
            }, timeout=30)
            if response.ok:
                new = response.json()
                new.setdefault("refresh_token", token["refresh_token"])
                return save_token(new)
    return browser_login(client_id)


# ---------------------------------------------------------------------------
# Talking to the Spotify API
# ---------------------------------------------------------------------------
class Spotify:
    def __init__(self, client_id):
        self.client_id = client_id
        self.token = get_token(client_id)
        self.cache = {}

    def get(self, url, params=None):
        if not url.startswith("http"):
            url = API + url
        for attempt in range(5):
            if time.time() >= self.token.get("expires_at", 0):
                self.token = get_token(self.client_id)
            response = requests.get(
                url, params=params, timeout=30,
                headers={"Authorization": f"Bearer {self.token['access_token']}"},
            )
            if response.status_code == 429:  # too many requests: wait and retry
                wait = int(response.headers.get("Retry-After", 5)) + 1
                print(f"  Spotify asked us to slow down; waiting {wait}s...")
                time.sleep(wait)
                continue
            if response.status_code == 401 and attempt == 0:  # token went stale
                self.token["expires_at"] = 0
                continue
            response.raise_for_status()
            return response.json()
        sys.exit("Spotify kept refusing requests. Try again in a few minutes.")

    def get_cached(self, path):
        if path not in self.cache:
            self.cache[path] = self.get(path)
        return self.cache[path]

    def pages(self, path, params=None):
        """Yield every item across all pages of a list endpoint."""
        data = self.get(path, params)
        while True:
            yield from data.get("items", [])
            if not data.get("next"):
                break
            data = self.get(data["next"])

    def my_playlists(self):
        return list(self.pages("/me/playlists", {"limit": 50}))

    def playlist_items(self, playlist_id):
        return self.pages(f"/playlists/{playlist_id}/items", {"limit": 50})


def find_playlist(playlists, wanted):
    for p in playlists:
        if p["id"] == wanted:
            return p
    matches = [p for p in playlists if p["name"].strip().lower() == wanted.strip().lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        sys.exit(f'More than one playlist is called "{wanted}". Use its ID instead (see --list).')
    sys.exit(f'No playlist called "{wanted}". Run with --list to see your playlists.')


def song_row(sp, entry, playlist_name):
    """Turn one playlist entry into one row of Spotify columns (or None to skip)."""
    track = entry.get("item") or entry.get("track")  # Spotify renamed "track" to "item" in 2026
    if not track or track.get("type") != "track" or track.get("is_local") or not track.get("id"):
        return None  # podcast episodes, local files, removed songs

    artists = track.get("artists") or []
    main = artists[0] if artists else {}
    album_stub = track.get("album") or {}

    artist = sp.get_cached(f"/artists/{main['id']}") if main.get("id") else {}
    album = sp.get_cached(f"/albums/{album_stub['id']}") if album_stub.get("id") else album_stub
    images = album.get("images") or album_stub.get("images") or []
    biggest = max(images, key=lambda i: i.get("width") or 0)["url"] if images else ""
    release = album.get("release_date", "")

    return {
        "spotify_track_id": track["id"],
        "title": track.get("name", ""),
        "artist": main.get("name", ""),
        "featured_artists": "; ".join(a["name"] for a in artists[1:]),
        "spotify_artist_id": main.get("id", ""),
        "spotify_artist_url": (main.get("external_urls") or {}).get("spotify", ""),
        "genres": "; ".join(artist.get("genres") or []),
        "album": album.get("name", ""),
        "album_type": album.get("album_type", ""),
        "album_track_count": album.get("total_tracks", ""),
        "track_number": track.get("track_number", ""),
        "release_date": release,
        "release_month": release_month(release),
        "duration": ms_to_mss(track.get("duration_ms", 0)),
        "duration_ms": track.get("duration_ms", ""),
        "explicit": "yes" if track.get("explicit") else "no",
        "isrc": (track.get("external_ids") or {}).get("isrc", ""),
        "upc": (album.get("external_ids") or {}).get("upc", ""),
        "spotify_url": (track.get("external_urls") or {}).get("spotify", ""),
        "cover_url": biggest,
        "playlists": playlist_name,
        "first_added_at": (entry.get("added_at") or "")[:10],
    }


# ---------------------------------------------------------------------------
# Reading and writing the master file
# ---------------------------------------------------------------------------
def read_master():
    if not MASTER_CSV.exists():
        return {}, []
    with MASTER_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = {row["spotify_track_id"]: row for row in reader}
        return rows, reader.fieldnames or []


def write_master(rows, existing_columns):
    extra = [c for c in existing_columns if c not in SPOTIFY_COLUMNS]
    columns = SPOTIFY_COLUMNS + extra
    MASTER_CSV.parent.mkdir(exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (r.get("artist", "").lower(), r.get("title", "").lower()))
    with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ordered)


def merge(master, new):
    """Update Spotify columns; keep every other column; combine playlists."""
    old = master.get(new["spotify_track_id"], {})
    merged = dict(old)
    merged.update(new)
    lists = split_list(old.get("playlists")) + split_list(new["playlists"])
    merged["playlists"] = "; ".join(dict.fromkeys(lists))
    dates = [d for d in (old.get("first_added_at"), new["first_added_at"]) if d]
    merged["first_added_at"] = min(dates) if dates else ""
    merged["spotify_pulled_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    master[new["spotify_track_id"]] = merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Pull Spotify playlists into data/master.csv")
    parser.add_argument("--list", action="store_true", help="show your playlists and stop")
    parser.add_argument("--playlist", action="append", default=[], help="playlist name or ID (repeatable)")
    args = parser.parse_args()

    load_env()
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        sys.exit("No SPOTIFY_CLIENT_ID found. Add it to a .env file (see docs/track-database.md).")

    sp = Spotify(client_id)
    playlists = sp.my_playlists()

    if args.list or not args.playlist:
        print(f"\nYour playlists ({len(playlists)}):\n")
        for p in playlists:
            count = (p.get("items") or p.get("tracks") or {}).get("total", "?")
            print(f"  {p['name']:<45} {count:>4} songs   ID: {p['id']}")
        if not args.playlist:
            print('\nNext: python tools/pull_spotify.py --playlist "Playlist name"')
        return

    master, columns = read_master()
    before = len(master)
    for wanted in args.playlist:
        playlist = find_playlist(playlists, wanted)
        print(f'\nPulling "{playlist["name"]}"...')
        count = 0
        for entry in sp.playlist_items(playlist["id"]):
            row = song_row(sp, entry, playlist["name"])
            if row:
                merge(master, row)
                count += 1
                print(f"  {count:>3}. {row['artist']} - {row['title']}")
        print(f"  Done: {count} songs.")

    write_master(master, columns)
    print(f"\nSaved {len(master)} songs to {MASTER_CSV.relative_to(REPO)} "
          f"({len(master) - before} new).")


if __name__ == "__main__":
    main()
