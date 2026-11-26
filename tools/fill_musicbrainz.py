"""
Fill the master data set (data/master.csv) with details from MusicBrainz.

Step 2 of the track database. Runs in GitHub Actions ("Fill from MusicBrainz").
Adds mb_* columns; never touches the Spotify columns.

How it finds each song:
  1. By ISRC (the song's universal ID, from Spotify)  -> song, release, label,
     songwriters, producers, and the artist.
  2. If the ISRC isn't in MusicBrainz, by the artist's Spotify link -> artist
     details only (hometown, formed, links), no label or songwriters.

MusicBrainz is free and needs no key, but asks for at most one request per
second and a contact address in the User-Agent. This script follows both.

Usage:
    python tools/fill_musicbrainz.py            only songs not checked yet
    python tools/fill_musicbrainz.py --refresh  re-check every song
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
MASTER_CSV = REPO / "data" / "master.csv"
API = "https://musicbrainz.org/ws/2"
USER_AGENT = "UnchartedTracks/1.0 ( https://github.com/danielwipert/uncharted.tracks )"

MB_COLUMNS = [
    "mb_match",            # how it was found: isrc / spotify-artist-link / not found
    "mb_label",
    "mb_catalog_number",
    "mb_release_country",
    "mb_songwriters",      # composers, lyricists, writers ("; " separated)
    "mb_producers",
    "mb_hometown",         # where the artist was formed or born, e.g. "Belfast, United Kingdom"
    "mb_country",
    "mb_formed",           # year formed (or born)
    "mb_disbanded",        # year split up, if they did
    "mb_artist_type",      # Group / Person
    "mb_members",
    "mb_bandcamp_url",
    "mb_official_site",
    "mb_instagram",
    "mb_other_links",
    "mb_tags",             # genre tags from MusicBrainz users
    "mb_recording_id",
    "mb_artist_id",
    "mb_checked_at",
]


class MusicBrainz:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.last = 0.0
        self.cache = {}

    def get(self, path, **params):
        key = (path, tuple(sorted(params.items())))
        if key in self.cache:
            return self.cache[key]
        params["fmt"] = "json"
        for attempt in range(6):
            wait = 1.1 - (time.time() - self.last)  # one request per second
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                response = self.session.get(API + path, params=params, timeout=30)
            except requests.RequestException:
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 404:
                self.cache[key] = None
                return None
            if response.status_code in (429, 500, 502, 503, 504):  # busy: back off and retry
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            self.cache[key] = response.json()
            return self.cache[key]
        print(f"  ::warning::MusicBrainz didn't answer for {path}; skipping.")
        return None


def year(text):
    return (text or "")[:4]


def join(items):
    return "; ".join(dict.fromkeys(i for i in items if i))


def rel_names(relations, types, target="artist"):
    return [r[target]["name"] for r in relations or []
            if r.get("type") in types and r.get(target)]


def pick_release(releases, upc):
    """Prefer the release whose barcode matches Spotify's UPC, then the earliest official one."""
    if not releases:
        return None
    for r in releases:
        if upc and (r.get("barcode") or "").lstrip("0") == upc.lstrip("0"):
            return r
    official = [r for r in releases if r.get("status") == "Official"] or releases
    return sorted(official, key=lambda r: r.get("date") or "9999")[0]


def artist_details(mb, artist_id):
    artist = mb.get(f"/artist/{artist_id}", inc="url-rels+tags+genres+artist-rels")
    if not artist:
        return {}
    rels = artist.get("relations") or []
    begin_area = (artist.get("begin-area") or {}).get("name", "")
    area = (artist.get("area") or {}).get("name", "")
    hometown = ", ".join(x for x in dict.fromkeys([begin_area, area]) if x)

    links = {"bandcamp": "", "official": "", "instagram": "", "other": []}
    for r in rels:
        url = (r.get("url") or {}).get("resource", "")
        if not url:
            continue
        if "bandcamp.com" in url and not links["bandcamp"]:
            links["bandcamp"] = url
        elif r.get("type") == "official homepage" and not links["official"]:
            links["official"] = url
        elif "instagram.com" in url and not links["instagram"]:
            links["instagram"] = url
        elif r.get("type") in ("social network", "youtube", "soundcloud", "official homepage"):
            links["other"].append(url)

    members = [r["artist"]["name"] for r in rels
               if r.get("type") == "member of band" and r.get("direction") == "backward" and r.get("artist")]
    tags = sorted(artist.get("genres") or artist.get("tags") or [], key=lambda t: -t.get("count", 0))

    return {
        "mb_artist_id": artist_id,
        "mb_hometown": hometown,
        "mb_country": area if area != begin_area else "",
        "mb_formed": year((artist.get("life-span") or {}).get("begin")),
        "mb_disbanded": year((artist.get("life-span") or {}).get("end")),
        "mb_artist_type": artist.get("type") or "",
        "mb_members": join(members),
        "mb_bandcamp_url": links["bandcamp"],
        "mb_official_site": links["official"],
        "mb_instagram": links["instagram"],
        "mb_other_links": join(links["other"][:5]),
        "mb_tags": join(t["name"] for t in tags[:5]),
    }


def by_isrc(mb, row):
    found = mb.get(f"/isrc/{row['isrc']}") if row.get("isrc") else None
    recordings = (found or {}).get("recordings") or []
    if not recordings:
        return None

    # Prefer the recording whose main artist matches Spotify's.
    def same_artist(rec):
        credits = rec.get("artist-credit") or []
        return bool(credits) and credits[0].get("name", "").lower() == row["artist"].lower()
    recording_id = next((r["id"] for r in recordings if same_artist(r)), recordings[0]["id"])

    rec = mb.get(f"/recording/{recording_id}", inc="artist-credits+releases+work-rels+artist-rels")
    if not rec:
        return None
    out = {"mb_match": "isrc", "mb_recording_id": recording_id}

    rec_rels = rec.get("relations") or []
    out["mb_producers"] = join(rel_names(rec_rels, {"producer"}))
    writers = rel_names(rec_rels, {"composer", "lyricist", "writer"})
    for r in rec_rels:
        if r.get("target-type") == "work" and r.get("work"):
            work = mb.get(f"/work/{r['work']['id']}", inc="artist-rels")
            if work:
                writers += rel_names(work.get("relations"), {"composer", "lyricist", "writer"})
    out["mb_songwriters"] = join(writers)

    release = pick_release(rec.get("releases"), row.get("upc"))
    if release:
        full = mb.get(f"/release/{release['id']}", inc="labels") or {}
        label_info = full.get("label-info") or []
        out["mb_label"] = join((li.get("label") or {}).get("name") for li in label_info)
        out["mb_catalog_number"] = join(li.get("catalog-number") for li in label_info
                                        if li.get("catalog-number") not in (None, "[none]"))
        out["mb_release_country"] = full.get("country") or release.get("country") or ""

    credits = rec.get("artist-credit") or []
    if credits and credits[0].get("artist"):
        out.update(artist_details(mb, credits[0]["artist"]["id"]))
    return out


def by_spotify_link(mb, row):
    url = row.get("spotify_artist_url")
    if not url:
        return None
    found = mb.get("/url", resource=url, inc="artist-rels")
    rels = (found or {}).get("relations") or []
    artist = next((r["artist"] for r in rels if r.get("artist")), None)
    if not artist:
        return None
    out = {"mb_match": "spotify-artist-link"}
    out.update(artist_details(mb, artist["id"]))
    return out


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main():
    parser = argparse.ArgumentParser(description="Fill data/master.csv from MusicBrainz")
    parser.add_argument("--refresh", action="store_true", help="re-check songs already checked")
    args = parser.parse_args()

    if not MASTER_CSV.exists():
        sys.exit("::error::data/master.csv not found. Run 'Pull from Spotify' first.")
    with MASTER_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = list(reader.fieldnames or [])
    columns += [c for c in MB_COLUMNS if c not in columns]

    mb = MusicBrainz()
    todo = [r for r in rows if args.refresh or not r.get("mb_checked_at")]
    print(f"Checking {len(todo)} of {len(rows)} songs on MusicBrainz (about {len(todo) * 5} seconds)...\n")
    counts = {"isrc": 0, "spotify-artist-link": 0, "not found": 0}

    for i, row in enumerate(todo, 1):
        found = by_isrc(mb, row) or by_spotify_link(mb, row) or {"mb_match": "not found"}
        for c in MB_COLUMNS:
            row[c] = found.get(c, "")
        row["mb_checked_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        counts[row["mb_match"]] += 1
        bits = [x for x in (row["mb_label"], row["mb_hometown"]) if x]
        print(f"  {i:>3}. {row['artist']} - {row['title']}: {row['mb_match']}"
              + (f" ({' | '.join(bits)})" if bits else ""))

        if i % 10 == 0 or i == len(todo):  # save as we go, so a stopped run keeps its work
            with MASTER_CSV.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)

    filled = {c: sum(1 for r in rows if r.get(c)) for c in
              ("mb_label", "mb_hometown", "mb_songwriters", "mb_formed", "mb_bandcamp_url")}
    lines = [
        "## Fill from MusicBrainz", "",
        f"Checked **{len(todo)}** songs: {counts['isrc']} found by ISRC, "
        f"{counts['spotify-artist-link']} artist-only (via Spotify link), {counts['not found']} not found.", "",
        "| Field | Songs filled |", "|---|---|",
    ] + [f"| {c.replace('mb_', '')} | {n} of {len(rows)} |" for c, n in filled.items()]
    print("\n" + "\n".join(lines[2:3]))
    summary("\n".join(lines))


if __name__ == "__main__":
    main()
